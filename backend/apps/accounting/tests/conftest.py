import django.template.context
import copy as _copy


def _patched_context_copy(self):
    duplicate = django.template.context.BaseContext.__new__(type(self))
    duplicate.dicts = self.dicts[:]
    return duplicate


django.template.context.Context.__copy__ = _patched_context_copy
django.template.context.RenderContext.__copy__ = _patched_context_copy
django.template.context.RequestContext.__copy__ = _patched_context_copy
