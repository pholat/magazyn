from lagom import Container, Singleton
from database import Database
from services import AuthService, ItemService

container = Container()
container[Database] = Singleton(lambda: Database("sqlite:///./app.db"))
container[AuthService] = AuthService
container[ItemService] = ItemService
