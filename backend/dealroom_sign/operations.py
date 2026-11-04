"""Extend Send's registry; its dispatch, tier, approval and activity hooks stay authoritative."""

def install():
    from dealroom import registry
    registry.STAFF.update({'SigningEnvelopeViewSet', 'SignCredentialView', 'SigningNdaPolicyView'})
    registry.PUBLIC.update({'RecipientNdaView', 'RecipientNdaEnterView'})
    registry.HUMAN_ONLY.add(('SignCredentialView', 'put'))
    # All signing mutations either expose a new recipient or alter the gate. The
    # default evaluate_change classification treats their unlisted fields as widening.
    # GET returns a redacted projection only; credentials are human-write, never read.
