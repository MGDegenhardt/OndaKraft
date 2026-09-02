import os
import sys
import importlib.util
import inspect
from plugins import AudioPlugin


# Desenvolvimento da secao a partid de onde  plugins e efeitos sao carregados
# os plugins sao carregados somente a partir da pasta ./plugins
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class PluginLoader:
    def __init__(self, plugins_dir: str = "plugins"):
        """
        PluginLoader - Escaneia um diretório, importa scripts Python dinamicamente
        e descobre novas classes que estendem a classe 'AudioPlugin' [1].
        """
        self.plugins_dir = os.path.abspath(plugins_dir)
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)

    def discover_and_load(self) -> list[type[AudioPlugin]]:
        """
        Varre a pasta de plugins e importa cada classe filha de AudioPlugin [1].
        """
        loaded_plugin_classes = []
        if self.plugins_dir not in sys.path:
            sys.path.insert(0, self.plugins_dir)

        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and filename != "__init__.py" and filename != "plugins.py":
                module_name = filename[:-3]
                file_path = os.path.join(self.plugins_dir, filename)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Procura classes que herdam de AudioPlugin no arquivo importado
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, AudioPlugin) and obj is not AudioPlugin:
                            loaded_plugin_classes.append(obj)
                            print(f"Plugin detectado: {obj.__name__} (do arquivo {filename})")

                except Exception as err:
                    print(f"Erro ao carregar o arquivo {filename}: {err}")

        return loaded_plugin_classes