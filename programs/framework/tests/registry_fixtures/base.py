class FixtureBase:
    """Stands in for ProgramCalculator: something with a key attribute.

    Mirrors ProgramCalculator's abstract protocol so build() treats fixtures the
    same way it treats real calculators.
    """

    program_code = ""
    _abstract = True

    def __init_subclass__(cls, abstract: bool = False, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._abstract = abstract
