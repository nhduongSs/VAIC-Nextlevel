from enum import StrEnum


class ChunkType(StrEnum):
    ARTICLE = "ARTICLE"
    CLAUSE = "CLAUSE"
    PARAGRAPH = "PARAGRAPH"
    TABLE = "TABLE"
    DEFINITION = "DEFINITION"
    APPENDIX = "APPENDIX"
