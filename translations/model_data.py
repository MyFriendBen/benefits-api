from typing import TypedDict, Generic, TypeVar

T = TypeVar("T")


class ModelDataController(Generic[T]):
    _model_name = ""
    dependencies: list[str] = []

    DataType = TypedDict("DataType", {})

    class DeferCreation(Exception):
        pass

    def __init__(self, instance: T) -> None:
        self.instance = instance

    @property
    def model_name(self) -> str:
        return self._model_name if self._model_name != "" else self.instance.__class__.__name__

    @property
    def external_name(self) -> str:
        return self.instance.external_name

    def to_model_data(self) -> DataType:
        return {}

    def from_model_data(self, data: DataType) -> None:
        pass

    @classmethod
    def get_instance(cls, external_name: str, Model: type[T]) -> T:
        return Model.objects.get(external_name=external_name)

    @classmethod
    def create_instance(cls, external_name: str, Model: type[T]) -> T:
        raise NotImplemented('"create_instance" must be defined')

    @classmethod
    def initialize_instance(cls, external_name: str, Model: type[T]) -> T:
        try:
            return cls.get_instance(external_name, Model)
        except Model.DoesNotExist:
            return cls.create_instance(external_name, Model)
