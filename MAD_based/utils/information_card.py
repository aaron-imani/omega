# Trustworthiness enum
from enum import Enum


class Trustworthiness(Enum):
    HIGH = "This information is most likely correct and can be trusted."
    MEDIUM = "This information may be correct, but it is not guaranteed. If the validity information conflicts with other sources of higher trustworthiness, trust the other sources."
    LOW = "This information is most likely inaccurate. Trust this only if you have little to no other information for what you want to know."


class InformationCard:
    def __init__(
        self,
        title,
        information,
        learning_instructions=None,
        usage_instructions=None,
        reading_instructions=None,
        trustworthiness=None,
        heading_level=1,
    ):
        self.heading_level = heading_level
        self.subheading = "#" * (heading_level + 1)
        self.title = title
        self.information = information
        # self.learning_instructions = learning_instructions
        # self.usage_instructions = usage_instructions
        # self.reading_instructions = reading_instructions
        # self.trustworthiness = (
        #     trustworthiness.value if trustworthiness is not None else None
        # )
        self.metadata_attributes = {}
        if reading_instructions is not None:
            self.metadata_attributes["Reading Instructions"] = reading_instructions

        if trustworthiness is not None:
            self.metadata_attributes["Trustworthiness"] = trustworthiness.value

        if learning_instructions is not None:
            self.metadata_attributes["Learning Instructions"] = learning_instructions

        if usage_instructions is not None:
            self.metadata_attributes["Usage Instructions"] = usage_instructions

    def _make_heading(self, text):
        return ("#" * self.heading_level) + " " + text

    def _make_subheading(self, title, text):
        return self.subheading + " " + title + "\n\n" + text + "\n\n"

    def __str__(self):
        string_repr = self._make_heading(self.title) + "\n"
        string_repr += self.information + "\n\n"

        for title, value in self.metadata_attributes.items():
            string_repr += self._make_subheading(title, value)

        string_repr += "__" * 40 + "\n\n"
        return string_repr

    @staticmethod
    def get_strucuture():
        instructions = (
            "An information card is a structured way to present information in markdown format. It consists of the card title, the information itself, and metadata attributes. "
            "Metadata attributes include learning instructions, usage instructions, reading instructions, and trustworthiness. The title is the name of the information card, the information is the actual content, and metadata attributes are additional information about the information."
            "Learning instructions are instructions on how to learn from the information, usage instructions are instructions on how to use the information, reading instructions are instructions on how to read the information, and trustworthiness is the trustworthiness of the information."
        )
        return instructions
