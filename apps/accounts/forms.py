from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario


class BootstrapFormMixin:
    """Agrega las clases de Bootstrap a todos los widgets del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(widget, forms.Select):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f'{widget.attrs.get("class", "")} {clase}'.strip()


class _UsuarioBaseForm(BootstrapFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Regla del documento: todo usuario pertenece a un área.
        self.fields["area"].required = True
        self.fields["puesto"].required = False

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip()
        repetidos = Usuario.objects.filter(correo__iexact=correo)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        return correo

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1, self.instance)
                except ValidationError as error:
                    self.add_error("password1", error)
        return datos


class UsuarioCrearForm(_UsuarioBaseForm):
    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "area", "puesto"]
        labels = {"area": "Área"}

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])  # se guarda con hash
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(_UsuarioBaseForm):
    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "area", "puesto", "activo"]
        labels = {"area": "Área"}

    def __init__(self, *args, editando_a_si_mismo=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.password_cambiada = False
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["password1"].label = "Nueva contraseña"
        self.fields["password1"].help_text = "Déjala vacía para conservar la actual."
        if editando_a_si_mismo:
            # Evita que un admin se quite el rol o se desactive a sí mismo.
            self.fields["rol"].disabled = True
            self.fields["activo"].disabled = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            usuario.set_password(self.cleaned_data["password1"])
            self.password_cambiada = True
        if commit:
            usuario.save()
        return usuario
