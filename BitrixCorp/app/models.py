from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Company(Base):
	__tablename__ = "companies"

	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(255), nullable=False, index=True)

	contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
	__tablename__ = "contacts"

	id = Column(Integer, primary_key=True, index=True)
	first_name = Column(String(100), nullable=False)
	last_name = Column(String(100), nullable=False)
	gender = Column(String(10), nullable=False)
	age = Column(Integer, nullable=False)
	phone = Column(String(50), nullable=False)
	company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

	company = relationship("Company", back_populates="contacts")
