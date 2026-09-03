import os
import sys
import importlib.util
import inspect
from base_synth import BaseSynthesizer

# Desenvolvimento do modulo responsavel pela importação dos instrumentos
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class SynthLoader:
    def __init__(self, synths_dir: str = "synths"):
        """
        SynthLoader - Escaneia a pasta física "synths/", importa arquivos Python dinamicamente
        e descobre novas classes que estendam a classe base "BaseSynthesizer".
        """
        self.synths_dir = os.path.abspath(synths_dir)
        if not os.path.exists(self.synths_dir):
            os.makedirs(self.synths_dir)

    def discover_and_load(self) -> list[type[BaseSynthesizer]]:
        """
        Varre a pasta de sintetizadores e retorna uma lista das classes filhas de BaseSynthesizer encontradas.
        """
        loaded_synth_classes = []
        if self.synths_dir not in sys.path:
            sys.path.insert(0, self.synths_dir)

        # Adiciona o diretório atual do projeto também caso o usuário execute de fora
        project_root = os.path.dirname(self.synths_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        if not os.path.exists(self.synths_dir):
            return loaded_synth_classes

        for filename in os.listdir(self.synths_dir):
            if filename.endswith(".py") and filename != "__init__.py" and filename != "base_synth.py":
                module_name = filename[:-3]
                file_path = os.path.join(self.synths_dir, filename)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Procura classes que herdam de BaseSynthesizer no módulo
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseSynthesizer) and obj is not BaseSynthesizer:
                            loaded_synth_classes.append(obj)
                            print(f"Sintetizador importado dinamicamente: {obj.__name__} (do arquivo {filename})")

                except Exception as err:
                    print(f"Erro ao carregar o arquivo de synth {filename}: {err}")

        return loaded_synth_classes
