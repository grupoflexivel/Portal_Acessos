from django.forms.widgets import CheckboxSelectMultiple

class GrupoCheckboxSelectMultiple(CheckboxSelectMultiple):
    template_name = 'usuarios/widgets/grupo_checkbox_select.html'
    option_template_name = 'usuarios/widgets/grupo_checkbox_option.html'