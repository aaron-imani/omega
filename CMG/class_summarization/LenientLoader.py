from __future__ import annotations
from langchain_community.document_loaders.generic import GenericLoader
from langchain_core.documents import Document
from typing import Iterator
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Iterator,
    Literal,
    Optional,
    Sequence,
    Union,
)

from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseBlobParser
from langchain_community.document_loaders.blob_loaders import (
    FileSystemBlobLoader,
)
from langchain_community.document_loaders.parsers.registry import get_parser

if TYPE_CHECKING:
    pass

_PathLike = Union[str, Path]

DEFAULT = Literal["default"]


class LenientLoader(GenericLoader):
    def lazy_load(
        self,
    ) -> Iterator[Document]:
        """Load documents lazily. Use this when working at a large scale."""
        for blob in self.blob_loader.yield_blobs():
            try:
                yield from self.blob_parser.lazy_parse(blob)
            except UnicodeDecodeError:
                pass


    @classmethod
    def from_filesystem(
        cls,
        path: _PathLike,
        *,
        glob: str = "**/[!.]*",
        exclude: Sequence[str] = (),
        suffixes: Optional[Sequence[str]] = None,
        show_progress: bool = False,
        parser: Union[DEFAULT, BaseBlobParser] = "default",
        parser_kwargs: Optional[dict] = None,
    ) -> LenientLoader:
        """Create a generic document loader using a filesystem blob loader.

        Args:
            path: The path to the directory to load documents from OR the path to a
                  single file to load. If this is a file, glob, exclude, suffixes
                    will be ignored.
            glob: The glob pattern to use to find documents.
            suffixes: The suffixes to use to filter documents. If None, all files
                      matching the glob will be loaded.
            exclude: A list of patterns to exclude from the loader.
            show_progress: Whether to show a progress bar or not (requires tqdm).
                           Proxies to the file system loader.
            parser: A blob parser which knows how to parse blobs into documents,
                    will instantiate a default parser if not provided.
                    The default can be overridden by either passing a parser or
                    setting the class attribute `blob_parser` (the latter
                    should be used with inheritance).
            parser_kwargs: Keyword arguments to pass to the parser.

        Returns:
            A generic document loader.
        """
        blob_loader = FileSystemBlobLoader(
            path,
            glob=glob,
            exclude=exclude,
            suffixes=suffixes,
            show_progress=show_progress,
        )
        if isinstance(parser, str):
            if parser == "default":
                try:
                    # If there is an implementation of get_parser on the class, use it.
                    blob_parser = cls.get_parser(**(parser_kwargs or {}))
                except NotImplementedError:
                    # if not then use the global registry.
                    blob_parser = get_parser(parser)
            else:
                blob_parser = get_parser(parser)
        else:
            blob_parser = parser
        return cls(blob_loader, blob_parser)
