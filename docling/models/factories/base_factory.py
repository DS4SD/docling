import enum
import logging
from abc import ABCMeta
from typing import Generic, Optional, Type, TypeVar

from pluggy import PluginManager

from docling.datamodel.pipeline_options import BaseOptions
from docling.models.base_model import BaseModelWithOptions

A = TypeVar("A", bound=BaseModelWithOptions)


logger = logging.getLogger(__name__)


class BaseFactory(Generic[A], metaclass=ABCMeta):
    default_plugin_name = "docling"

    def __init__(self, plugin_attr_name: str, plugin_name=default_plugin_name):
        self.plugin_name = plugin_name
        self.plugin_attr_name = plugin_attr_name

        self._classes: dict[Type[BaseOptions], Type[A]] = {}

    @property
    def registered_kind(self) -> list[str]:
        return list(opt.kind for opt in self._classes.keys())

    def get_enum(self) -> enum.Enum:
        return enum.Enum(
            self.plugin_attr_name + "_enum",
            names={kind: kind for kind in self.registered_kind},
            type=str,
            module=__name__,
        )

    @property
    def classes(self):
        return self._classes

    def get_class(self, options: BaseOptions, *args, **kwargs) -> Type[A]:
        try:
            return self._classes[type(options)]
        except KeyError:
            return self.on_class_not_found(options.kind, *args, **kwargs)

    def get_class_by_kind(self, kind: str, *args, **kwargs) -> Type[A]:
        for opt, cls in self._classes.items():
            if opt.kind == kind:
                return cls
        return self.on_class_not_found(kind, *args, **kwargs)

    def get_options_class(self, kind: str, *args, **kwargs) -> Type[BaseOptions]:
        for opt, cls in self._classes.items():
            if opt.kind == kind:
                return opt
        return self.on_class_not_found(kind, *args, **kwargs)

    def on_class_not_found(self, kind: str, *args, **kwargs):
        msg = []

        for opt, cls in self._classes.items():
            msg.append(f"\t{opt.kind!r} => {cls!r}")

        msg_str = "\n".join(msg)

        raise RuntimeError(
            f"No class found with the name {kind!r}, known classes are:\n{msg_str}"
        )

    def register(self, cls: Type[A]):
        opt_type = cls.get_options_type()

        if opt_type in self._classes:
            raise ValueError(
                f"{opt_type.kind!r} already registered to class {self._classes[opt_type]!r}"
            )

        self._classes[opt_type] = cls

    def load_from_plugins(self, plugin_name: Optional[str] = None):
        plugin_name = plugin_name or self.plugin_name

        plugin_manager = PluginManager(plugin_name)
        plugin_manager.load_setuptools_entrypoints(plugin_name)

        for plugin_name, plugin_module in plugin_manager.list_name_plugin():

            attr = getattr(plugin_module, self.plugin_attr_name, None)

            if callable(attr):
                logger.info("Loading plugin %r", plugin_name)

                config = attr()
                self.process_plugin(config)

    def process_plugin(self, config):
        for item in config[self.plugin_attr_name]:
            try:
                self.register(item)
            except ValueError:
                logger.warning("%r already registered", item)
