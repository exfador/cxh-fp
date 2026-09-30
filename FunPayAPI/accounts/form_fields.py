from bs4.element import Tag

from FunPayAPI.accounts.constants import CHECKBOX_VALUE, IGNORED_INPUT_TYPES

FormValue = str | list[str]


def control_is_enabled(control: Tag) -> bool:
    if control.has_attr("disabled"):
        return False
    for fieldset in control.find_parents("fieldset"):
        if not fieldset.has_attr("disabled"):
            continue
        legend = fieldset.find("legend", recursive=False)
        if not legend or legend not in control.parents:
            return False
    return True


def option_is_enabled(option: Tag) -> bool:
    if option.has_attr("disabled"):
        return False
    return not any(
        group.has_attr("disabled") for group in option.find_parents("optgroup")
    )


def select_values(control: Tag) -> FormValue | None:
    group = control.find_parent(class_="form-group")
    if group and "hidden" in group.get("class", []):
        return None
    options = control.find_all("option")
    selected = [option for option in options if option.has_attr("selected")]
    if not control.has_attr("multiple"):
        enabled = [option for option in options if option_is_enabled(option)]
        selected = selected[-1:] if selected else enabled[:1]
    values = [
        option.get("value", option.get_text())
        for option in selected
        if option_is_enabled(option)
    ]
    if control.has_attr("multiple"):
        return values or None
    return values[-1] if values else None


def input_value(control: Tag, preserve_unchecked: bool) -> str | None:
    input_type = control.get("type", "text").lower()
    if input_type in IGNORED_INPUT_TYPES:
        return None
    if input_type in {"checkbox", "radio"}:
        if control.has_attr("checked"):
            return control.get("value", CHECKBOX_VALUE)
        return "" if preserve_unchecked and input_type == "checkbox" else None
    return control.get("value", "")


def control_value(control: Tag, preserve_unchecked: bool) -> FormValue | None:
    if control.name == "textarea":
        return control.get_text()
    if control.name == "select":
        return select_values(control)
    return input_value(control, preserve_unchecked)


def parse_form_fields(
    form: Tag,
    preserve_unchecked: bool = False,
    exclude_names: frozenset[str] = frozenset(),
) -> dict[str, FormValue]:
    result = {}
    for control in form.find_all(["input", "textarea", "select"]):
        name = control.get("name")
        if not name or name in exclude_names or not control_is_enabled(control):
            continue
        value = control_value(control, preserve_unchecked)
        if value is not None:
            result[name] = value
    return result
