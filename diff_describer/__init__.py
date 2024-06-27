from .describer import DiffDescriber
from .perturbator import DiffPerturbator

describer = DiffDescriber()
perturbator = DiffPerturbator()


def get_diff_description(diff: str):
    correct = describer.get_descriptions(diff)
    perturbed_diff = perturbator.perturb(diff)
    perturbed = describer.get_descriptions(perturbed_diff)
    return correct, perturbed


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
#                 }}"""

# correct, perturbed = get_diff_description(raw_diff)
# print(correct, end="\n\n")
# print(perturbed)
