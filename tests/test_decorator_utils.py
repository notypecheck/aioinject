from aioinject.decorators import add_parameters_to_signature


def test_add_parameters_to_signature_with_kwargs() -> None:
    def func(**kwargs: int) -> None:
        pass

    add_parameters_to_signature(func, parameters={"param": str})
