from django_auth_ldap.backend import LDAPBackend as _LDAPBackend


class LDAPBackend(_LDAPBackend):
    """LDAPBackend que só autentica colaboradores com vinculado_ad=True.

    A vinculação ao AD é opcional por colaborador. Quem não estiver marcado
    é tratado como "não encontrado" pelo LDAP, o que (com
    AUTH_LDAP_NO_NEW_USERS=True) faz a autenticação LDAP falhar e o Django
    cair para o ModelBackend, preservando o fluxo de senha local de sempre.
    """

    def get_or_build_user(self, username, ldap_user):
        model = self.get_user_model()
        query_value = username.lower()

        try:
            user = model.objects.get(
                username__iexact=query_value,
                vinculado_ad=True,
            )
        except model.DoesNotExist:
            user = model(username=query_value)
            built = True
        else:
            built = False

        return (user, built)
