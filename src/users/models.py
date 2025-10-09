from sqlalchemy.orm import Mapped,mapped_column

from src.database import Base


class User(Base):
    email: Mapped[str] = mapped_column(min_length=3,)