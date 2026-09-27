"""Research package public API with lazy dossier exports to avoid import cycles."""
__all__ = ['ResearchDossier', 'EvidenceBundle', 'build_research_dossier']

def __getattr__(name):
    if name in __all__:
        from .dossier import ResearchDossier, EvidenceBundle, build_research_dossier
        return {'ResearchDossier':ResearchDossier,'EvidenceBundle':EvidenceBundle,'build_research_dossier':build_research_dossier}[name]
    raise AttributeError(name)
