import random
import re
import sys
from typing import Dict, List

sys.path.append("..")
from common.log_config import get_logger

logger = get_logger("DiffPerturbator")
# random.seed(12)


class DiffPerturbator:
    def __init__(self):
        self._pertubators = [self._by_expansion, self._by_shifting]

    def _is_changed_line(self, line):
        return (line.startswith("-") and not line.startswith("---")) or (
            line.startswith("+") and not line.startswith("+++")
        )

    def perturb(self, diff):
        perturb_fn = random.choice(self._pertubators)
        logger.debug(f"Applying perturbation: {perturb_fn.__name__}")
        perturbed = perturb_fn(diff)
        logger.debug(f"Perturbed diff: {perturbed}")
        return perturbed

    def _add_signs(self, signs_to_add, hunk_body):
        perturbed_diff = []
        for i in range(len(hunk_body)):
            if i in signs_to_add:
                perturbed_diff.append(signs_to_add[i] + hunk_body[i][1:])
            else:
                perturbed_diff.append(hunk_body[i][1:])

        return perturbed_diff

    def _shift_changed_lines(
        self, hunk_body, shift: int = 1, sign=lambda x: x[0] == "+" or x[0] == "-"
    ) -> List[str]:
        """Shifts changed lines (lines starting with '-' or '+') up or down by a given number of lines."""
        signs_to_add = {}

        for i in range(len(hunk_body)):
            if self._is_changed_line(hunk_body[i]) and sign(hunk_body[i]):
                new_index = i + shift if 0 <= i + shift < len(hunk_body) else i
                signs_to_add[new_index] = hunk_body[i][0]
        return self._add_signs(signs_to_add, hunk_body)

    def _by_shifting(self, diff):
        hunks = self._get_hunks(diff)
        perturbed_diff = []
        shift = random.choice([-2, -1, 1, 2])
        logger.debug(f"Shifting by {shift} lines.")
        for header, hunk in hunks:
            perturbed_diff.extend(header[:-1])
            perturbed_hunk = self._shift_changed_lines(hunk, shift=shift)

            hunk_data = self._parse_hunk_header(header[-1])
            hunk_data["old_length"] = self._count_old_version_lines(perturbed_hunk)
            hunk_data["new_length"] = self._count_new_version_lines(perturbed_hunk)
            hunk_header_line = header[-1].split("@@")[2]
            perturbed_diff.append(
                self._make_hunk_header(**hunk_data) + hunk_header_line
            )
            perturbed_diff.extend(perturbed_hunk)
        return "\n".join(perturbed_diff)

    def _expand_changed_lines(self, hunk_body, expand_by: int = 1) -> List[str]:
        """Expands changed lines by adding N lines from the original content around each change.

        Args:
        - hunk_body (List[str]): List of lines in the hunk body.
        - expand_by (int): Number of lines to expand by. If positive, expands downwards; if negative, expands upwards.

        Returns:
        - List[str]: List of perturbed lines.
        """
        signs_to_add = {}
        i = len(hunk_body) - 1 if expand_by > 0 else 0
        direction = -1 if expand_by > 0 else 1
        while 0 <= i < len(hunk_body):
            prev_index = i - expand_by
            if self._is_changed_line(hunk_body[i]):
                signs_to_add[i] = hunk_body[i][0]
            if (
                0 <= prev_index < len(hunk_body)
                and (not self._is_changed_line(hunk_body[i]))
                and self._is_changed_line(hunk_body[prev_index])
            ):
                sign = hunk_body[prev_index][0]
                for j in range(i, prev_index, direction):
                    if not self._is_changed_line(hunk_body[j]):
                        signs_to_add[j] = sign
                i = prev_index
            else:
                i += direction

        return self._add_signs(signs_to_add, hunk_body)

    def _count_old_version_lines(self, hunk_body):
        return (
            sum(
                1
                for line in hunk_body
                if line.startswith("-") or not line.startswith("+")
            )
            + 1
        )

    def _count_new_version_lines(self, hunk_body):
        return (
            sum(
                1
                for line in hunk_body
                if line.startswith("+") or not line.startswith("-")
            )
            + 1
        )

    def _make_hunk_header(self, old_start, old_length, new_start, new_length):
        return f"@@ -{old_start},{old_length} +{new_start},{new_length} @@"

    def _by_expansion(self, diff):
        hunks = self._get_hunks(diff)
        perturbed_diff = []
        expansion = random.choice([-2, -1, 1, 2])
        logger.debug(f"Expanding by {expansion} lines.")
        for header, hunk in hunks:
            perturbed_diff.extend(header[:-1])
            perturbed_hunk = self._expand_changed_lines(hunk, expand_by=expansion)
            hunk_data = self._parse_hunk_header(header[-1])
            hunk_data["old_length"] = self._count_old_version_lines(perturbed_hunk)
            hunk_data["new_length"] = self._count_new_version_lines(perturbed_hunk)
            hunk_header_line = header[-1].split("@@")[2]
            perturbed_diff.append(
                self._make_hunk_header(**hunk_data) + hunk_header_line
            )
            perturbed_diff.extend(perturbed_hunk)
        return "\n".join(perturbed_diff)

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

    def _get_hunks(self, diff: str) -> List[List[str]]:
        """Extracts hunk bodies from a git diff."""
        diff = diff.splitlines()
        hunks = []
        i = 0
        hunk_header = []
        while i < len(diff):
            if diff[i].startswith("@@"):
                start_index = i + 1
                j = start_index
                cur_hunk = []
                hunk_header.append(diff[i])
                while (
                    j < len(diff)
                    and not diff[j].startswith("diff --git")
                    and not diff[j].startswith("@@")
                ):
                    cur_hunk.append(diff[j])
                    j += 1
                hunks.append((hunk_header, cur_hunk))
                i = j
                hunk_header = []
            else:
                hunk_header.append(diff[i])
                i += 1
        return hunks


# Example Usage
# diff = """\
# diff --git a/example.py b/example.py
# index 83db48f..f7c1b3b 100644
# --- a/example.py
# +++ b/example.py
# @@ -1,5 +1,5 @@
# -def old_function():
# -    return "Old Function"
# +def new_function():
# +    return "New Function"
# """

# diff_perturbator = DiffPerturbator(diff)
# perturbed_diff = diff_perturbator.get_perturbed_diff()
# print(perturbed_diff)

# Sample git diff text
# git_diff = """diff --git "a/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt" "b/plugins/kotlin/j2k/services/src/org/jetbrains/kotlin/nj2k/postProcessing/processings/inspe\321\201tionLikeProcessings.kt"
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

# perturbator = DiffPerturbator()
# hunks = perturbator._get_hunks(git_diff)

# for header, hunk in hunks:
#     # print("\n".join(header))
#     print("\n".join(hunk) + "\n" + "-" * 50)
#     preturbed = perturbator._shift_changed_lines(hunk, shift=1)
#     print("Shifted by 1")
#     print("\n".join(preturbed) + "\n" + "-" * 50)
#     preturbed = perturbator._shift_changed_lines(hunk, shift=3)
#     print("Expand top -1")
#     print("\n".join(preturbed) + "\n" + "-" * 50)

#     print("\n" + "=" * 50 + "\n")

# print(perturbator.perturb(git_diff))
