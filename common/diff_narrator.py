import re
import sys
from typing import Dict, List, Tuple, Union

sys.path.append("..")
from common.log_config import get_logger

logger = get_logger("DiffNarrator")
Change = Union[Tuple[int, str], Tuple[int, str, int, str]]


class DiffNarrator:
    """
    A class to describe all the changes in a unified diff of Java files.
    """

    def __init__(self, show_line_types):
        self.show_line_types = show_line_types

    def get_narrative(self, diff):
        self.diff = diff
        self._descriptions = ""
        self._parse_diff()
        return self._descriptions

    def _add_description(self, description: str):
        """
        Add a description to the list of descriptions.

        Args:
        - description (str): Description to be added.
        """
        self._descriptions += description.lstrip()

    def _parse_hunk_header(self, header: str) -> Dict[str, int]:
        """
        Parse a hunk header line to extract old and new start lines and lengths.

        Args:
        - header (str): Hunk header line, e.g., @@ -10,7 +10,6 @@

        Returns:
        - dict: Dictionary containing 'old_start', 'old_length', 'new_start', and 'new_length' values.
        """
        match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", header)
        if match:
            old_start = int(match.group(1))
            old_length = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_length = int(match.group(4)) if match.group(4) else 1

            return {
                "old_start": old_start,
                "old_length": old_length,
                "new_start": new_start,
                "new_length": new_length,
            }
        else:
            return {"old_start": 0, "old_length": 0, "new_start": 0, "new_length": 0}

    def _parse_diff_header(self, line: str) -> str:
        """
        Parse the diff header to extract the filename.

        Args:
        - line (str): Diff header line, e.g., diff --git a/file.txt b/file.txt

        Returns:
        - str: The filename being diffed.
        """
        match = re.match(r"diff --git \"?a/([^\"]+)\"? \"?b/([^\"]+)\"?", line)
        if match:
            return match.group(1), match.group(2)
        else:
            return "unknown_file"

    def _join_lines(self, lines):
        lines = [l.strip() for l in lines]
        joined_lines = "\\n".join(lines)
        return f'"{joined_lines}"'

    def _get_line_type(self, line):
        line = line.strip()
        logger.debug(f"Processing line: {line}")
        if line.startswith("//"):
            return "comment"
        elif line.startswith("/*") or line.endswith("*/") or line.startswith("*"):
            return "Javadoc"
        # elif line.startswith("import"):
        #     return "import statement"
        # elif line.startswith("package"):
        #     return "package declaration"
        # elif line.startswith("@"):
        #     return "annotation"
        else:
            return "code"

    def _get_lines_type(self, lines: List[str]):
        if not self.show_line_types:
            return ""

        first_line = lines[0]
        last_line = lines[-1]
        first_line_type = self._get_line_type(first_line)
        last_line_type = self._get_line_type(last_line)
        logger.debug(f"First line type: {first_line_type}")
        logger.debug(f"Last line type: {last_line_type}")
        if first_line_type == last_line_type:
            return first_line_type
        else:
            return ""

    def _add_replaced_lines_description(self, removed_lines, added_lines):
        old_lines = [l for _, l in removed_lines]
        new_lines = [l for _, l in added_lines]

        # old_lines_str = self._join_lines(old_lines)
        # new_lines_str = self._join_lines(new_lines)
        old_lines_type = self._get_lines_type(old_lines)
        new_lines_type = self._get_lines_type(new_lines)
        # old_plural = "s" if len(removed_lines) > 1 else ""
        # new_plural = "s" if len(added_lines) > 1 else ""
        new_lines_str = "\n".join(new_lines)
        old_lines_str = "\n".join(old_lines)
        desc = f"{self._change_num}.\nFollowing {old_lines_type} line(s)\n```\n{old_lines_str}\n```\nis replaced with with following {new_lines_type} line(s)\n```\n{new_lines_str}\n```\n\n"

        self._add_description(desc)
        self._change_num += 1
        # self._add_description(
        #     f"{old_lines_type} line{old_plural} {old_lines_str} have been replaced with {new_lines_type} line{new_plural} {new_lines_str} in line {removed_lines[0][0]}\n\n"
        # )

    def _indentify_replaced_lines(self, removed_lines, added_lines):
        if removed_lines and added_lines and removed_lines[0][0] == added_lines[0][0]:
            self._add_replaced_lines_description(removed_lines, added_lines)
            return True
        return False

    def _parse_diff(self):
        current_file = None
        current_hunk = None
        self._change_num = 1

        lines = self.diff.splitlines()
        i = 0

        # last_edit = None
        removed_lines = []
        added_lines = []

        while i < len(lines):
            line = lines[i]

            if line.startswith("diff --git"):
                # parsed_header =
                current_file, new_name = self._parse_diff_header(line)
                logger.debug(f"Processing file: {current_file}")
                logger.debug(f"New name: {new_name}")
                self._add_description(
                    f"File {current_file} has been modified in this commit. "
                )
                if new_name != current_file:
                    self._add_description(f"It has been renamed to {new_name}.")

                self._add_description(
                    "\n\nFollowing changes have been made to the file:\n\n"
                )
                i += 1
                continue

            if line.startswith("@@"):
                current_hunk = self._parse_hunk_header(line)
                logger.debug(f"Processing hunk: {current_hunk}")
                old_lines_to_process = current_hunk["old_length"]
                new_lines_to_process = current_hunk["new_length"]
                last_edit = None
                removed_lines = []
                added_lines = []
                i += 1
                continue

            if current_file and current_hunk:
                if line.startswith("+") and not line.startswith("+++"):
                    if last_edit == "-" and added_lines:
                        self._add_replaced_lines_description(removed_lines, added_lines)
                        removed_lines = []
                        added_lines = []

                    current_line_number = (
                        current_hunk["new_start"]
                        + current_hunk["new_length"]
                        - new_lines_to_process
                    )
                    added_lines.append((current_line_number, line[1:]))
                    last_edit = "+"
                    new_lines_to_process -= 1

                elif line.startswith("-") and not line.startswith("---"):
                    if last_edit == "+" and added_lines:
                        self._add_replaced_lines_description(removed_lines, added_lines)
                        removed_lines = []
                        added_lines = []
                    current_line_number = (
                        current_hunk["old_start"]
                        + current_hunk["old_length"]
                        - old_lines_to_process
                    )
                    removed_lines.append((current_line_number, line[1:]))
                    last_edit = "-"
                    old_lines_to_process -= 1
                elif not line.startswith("+") and not line.startswith("-"):
                    if added_lines and removed_lines:
                        self._add_replaced_lines_description(removed_lines, added_lines)
                        removed_lines = []
                        added_lines = []
                    elif removed_lines:
                        old_lines = [l for _, l in removed_lines]
                        # old_lines_str = self._join_lines(old_lines)
                        old_lines_type = self._get_lines_type(old_lines)

                        old_lines_str = "\n".join(old_lines)
                        self._add_description(
                            f"{self._change_num}. Following {old_lines_type} line(s) are removed:\n\n```\n{old_lines_str}\n```\n\n"
                        )
                        self._change_num += 1
                        # if len(removed_lines) > 1:
                        #     self._add_description(
                        #         f"{old_lines_type} lines {removed_lines[0][0]} to {removed_lines[-1][0]} have been removed:\n{old_lines_str}\n\n"
                        #     )
                        # else:
                        #     self._add_description(
                        #         f"{old_lines_type} line {removed_lines[0][0]} has been removed:\n{old_lines_str}\n\n"
                        #     )

                        removed_lines = []
                    elif added_lines:
                        new_lines = [l for _, l in added_lines]
                        new_lines_type = self._get_lines_type(new_lines)
                        # new_lines_str = self._join_lines(new_lines)
                        plural = "s" if len(added_lines) > 1 else ""
                        # self._add_description(
                        #     f"Following {new_lines_type} line{plural} have been inserted after line {added_lines[0][0]}:\n{new_lines_str}\n\n"
                        # )
                        new_lines_str = "\n".join(new_lines)
                        self._add_description(
                            f"{self._change_num}. Following {new_lines_type} line{plural} are inserted after line {added_lines[0][0]}:\n\n```\n{new_lines_str}\n```\n\n"
                        )
                        self._change_num += 1
                        added_lines = []
                    old_lines_to_process -= 1
                    new_lines_to_process -= 1
            i += 1

        if added_lines and removed_lines:
            self._add_replaced_lines_description(removed_lines, added_lines)
            removed_lines = []
            added_lines = []
        elif removed_lines:
            old_lines = [l for _, l in removed_lines]
            # old_lines_str = self._join_lines(old_lines)
            old_lines_type = self._get_lines_type(old_lines)
            # if len(removed_lines) > 1:
            #     self._add_description(
            #         f"{old_lines_type} lines {removed_lines[0][0]} to {removed_lines[-1][0]} have been removed:\n{old_lines_str}\n\n"
            #     )
            # else:
            #     self._add_description(
            #         f"{old_lines_type} line {removed_lines[0][0]} has been removed:\n{old_lines_str}\n\n"
            #     )
            old_lines_str = "\n".join(old_lines)
            self._add_description(
                f"{self._change_num}. Following {old_lines_type} line(s) are removed:\n\n```\n{old_lines_str}\n```\n\n"
            )
            self._change_num += 1
            removed_lines = []
        elif added_lines:
            new_lines = [l for _, l in added_lines]
            new_lines_type = self._get_lines_type(new_lines)
            # new_lines_str = self._join_lines(new_lines)
            plural = "s" if len(added_lines) > 1 else ""
            # self._add_description(
            #     f"Following {new_lines_type} line{plural} have been inserted after line {added_lines[0][0]}:\n{new_lines_str}\n\n"
            # )
            new_lines_str = "\n".join(new_lines)
            self._add_description(
                f"{self._change_num}. Following {new_lines_type} line{plural} are inserted after line {added_lines[0][0]}:\n\n```\n{new_lines_str}\n```"
            )
            added_lines = []


narrator = DiffNarrator(False)

if __name__ == "__main__":
    import sys

    sys.path.append("..")
    from CMG.Agent_tools import get_git_diff_from_commit_url

    cm_url = input("Enter the commit url: ")
    diff = get_git_diff_from_commit_url(cm_url)
    narrative = narrator.get_narrative(diff)
    print(narrative)


# Example usage:
# raw_diff = """diff --git a/src/main/org/apache/tools/ant/taskdefs/condition/Os.java b/src/main/org/apache/tools/ant/taskdefs/condition/Os.java
# index 616d5790a..f8feeb16e 100644
# --- a/src/main/org/apache/tools/ant/taskdefs/condition/Os.java
# +++ b/src/main/org/apache/tools/ant/taskdefs/condition/Os.java
# @@ -65,8 +65,24 @@ import org.apache.tools.ant.BuildException;
#  public class Os implements Condition {{
#      private String family;

# +    /**
# +     * Sets the desired OS family type
# +     *
# +     * @param f      The OS family type desired<br />
# +     *               Possible values:<br />
# +     *               <ul><li>dos</li>
# +     *               <li>mac</li>
# +     *               <li>netware</li>
# +     *               <li>unix</li>
# +     *               <li>windows</li></ul>
# +     */
#      public void setFamily(String f) {{family = f.toLowerCase();}}

# +    /**
# +     * Determines if the OS on which Ant is executing matches the type of
# +     * that set in setFamily.
# +     * @see Os#setFamily(String)
# +     */
#      public boolean eval() throws BuildException {{
#          String osName = System.getProperty("os.name").toLowerCase();
#          String pathSep = System.getProperty("path.separator");"""


# raw_diff = """diff --git a/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java b/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# index b1a3f9bd49..e4c13c2c24 100644
# --- a/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# +++ b/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# @@ -122,8 +122,7 @@ public final class WicketTagIdentifier extends AbstractMarkupFilter
#                                                 "The wicket:id attribute value must not be empty. May be unmatched quotes?!?",
#                                                 tag.getPos());
#                         }}
# -                       // Make it a org.apache.wicket component. Otherwise it would be
# -                       // RawMarkup
# +                       // Make it a wicket component. Otherwise it would be RawMarkup
#                         tag.setId(value);
#                 }}
#                 """

# raw_diff = """diff --git "a/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt" "b/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt"
# index f474062f631c..9cd9bb07d37d 100644
# --- "a/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt"
# +++ "b/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt"
# @@ -352,7 +352,7 @@ class RemoveRedundantModalityModifierProcessing : ApplicabilityBasedInspectionLi
#      }

#      override fun apply(element: KtDeclaration) {
# -        element.removeModifierSmart(element.modalityModifierType()!!)
# +        element.removeModifier(element.modalityModifierType()!!)
#      }
#  }

# @@ -371,7 +371,7 @@ class RemoveRedundantVisibilityModifierProcessing : ApplicabilityBasedInspection
#      }

#      override fun apply(element: KtDeclaration) {
# -        element.removeModifierSmart(element.visibilityModifierType()!!)
# +        element.removeModifier(element.visibilityModifierType()!!)
#      }
#  }

# diff --git a/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/utils.kt b/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/utils.kt
# index a71c304c4aea..d41c3c52efa7 100644
# --- a/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/utils.kt
# +++ b/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/utils.kt
# @@ -75,14 +75,5 @@ fun KtElement.hasUsagesOutsideOf(inElement: KtElement, outsideElements: List<KtE
#          outsideElements.none { it.isAncestor(reference.element) }
#      }

# -
# -//hack until KT-30804 is fixed
# -fun KtModifierListOwner.removeModifierSmart(modifierToken: KtModifierKeywordToken) {
# -    val newElement = copy() as KtModifierListOwner
# -    newElement.removeModifier(modifierToken)
# -    replace(newElement)
# -    containingFile.commitAndUnblockDocument()
# -}
# -
#  inline fun <reified T : PsiElement> List<PsiElement>.descendantsOfType(): List<T> =
#      flatMap { it.collectDescendantsOfType() }
# \ No newline at end of file"""

# raw_diff = """diff --git a/example.txt b/example.txt
# index e69de29..b737feb 100644
# --- a/example.txt
# +++ b/example.txt
# @@ -1,7 +1,5 @@ Line 1: This is the first line.
# -Line 2: This is the second line.
# -Line 3: This is the third line.
# +Line 4: This is the fourth line.
# +Line 5: This line has been changed.
# -Line 6: This line has also been changed.
# -Line 7: This is the fifth line.
#  Line 8: This is the sixth line.
#  Line 9: This is the seventh line."""

# raw_diff = """diff --git a/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java b/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# index b1a3f9bd49..e4c13c2c24 100644
# --- a/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# +++ b/jdk-1.4/wicket/src/main/java/org/apache/wicket/markup/parser/filter/WicketTagIdentifier.java
# @@ -122,6 +122,7 @@ public final class WicketTagIdentifier extends AbstractMarkupFilter
#                                                "The wicket:id attribute value must not be empty. May be unmatched quotes?!?",
#                                                tag.getPos());
#                        }}
# -                       // Make it a org.apache.wicket component. Otherwise it would be
# -                       // RawMarkup
# +                       // Make it a wicket component. Otherwise it would be RawMarkup
# +                       tag.setId(value);
# +               }}"""

# raw_diff = """diff --git a/core/src/main/java/org/apache/cxf/staxutils/StaxSource.java b/core/src/main/java/org/apache/cxf/staxutils/StaxSource.java
# index 9b8dce22a3..5dea29b4ec 100644
# --- a/core/src/main/java/org/apache/cxf/staxutils/StaxSource.java
# +++ b/core/src/main/java/org/apache/cxf/staxutils/StaxSource.java
# @@ -66,8 +66,7 @@ public class StaxSource extends SAXSource implements XMLReader {
#                  // Attributes are handled in START_ELEMENT
#                  case XMLStreamConstants.ATTRIBUTE:
#                      break;
# -                case XMLStreamConstants.CDATA:
# -                {
# +                case XMLStreamConstants.CDATA: {
#                      if (lexicalHandler != null) {
#                          lexicalHandler.startCDATA();
#                      }
# @@ -80,16 +79,14 @@ public class StaxSource extends SAXSource implements XMLReader {
#                      }
#                      break;
#                  }
# -                case XMLStreamConstants.CHARACTERS:
# -                {
# +                case XMLStreamConstants.CHARACTERS: {
#                      int length = streamReader.getTextLength();
#                      int start = streamReader.getTextStart();
#                      char[] chars = streamReader.getTextCharacters();
#                      contentHandler.characters(chars, start, length);
#                      break;
#                  }
# -                case XMLStreamConstants.SPACE:
# -                {
# +                case XMLStreamConstants.SPACE: {
#                      int length = streamReader.getTextLength();
#                      int start = streamReader.getTextStart();
#                      char[] chars = streamReader.getTextCharacters();
# """
# explainer = DiffDescriber(False)
# descriptions = explainer.get_descriptions(raw_diff)
# logger.info(descriptions)
