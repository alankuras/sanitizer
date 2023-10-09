import subprocess
from typing import Iterable, Type, List, Dict, Tuple
from enum import Enum
from pathlib import Path
from log_file import LogFile


def get_command_output(command: str) -> Iterable[str]:
    for line in subprocess.run(f"http_proxy='' https_proxy='' {command}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.splitlines():
        yield line.decode("utf-8").strip()


class SOURCE(Enum):
    OPENSHIFT = "oc"
    KUBERNETES = "kubectl"


class LogFileFactory:
    def __init__(
        self, source: Type[SOURCE],
        logs_location: Type[Path] = None,
        namespaces: List = [],
        regexes: List[Dict[str, str]] = [],
        filters: Tuple[str, str] = (None, None)
    ):
        self._source = source
        self._logs_location = logs_location
        self._namespaces = namespaces
        self._regexes = regexes
        self._since, self._since_time, self._previous = filters

    def __iter__(self):
        return iter(self._logfiles())

    def __len__(self):
        return len(self._logfiles())

    def _logfiles(self) -> Iterable[Type[LogFile]]:
        filters, tags = self._prepare_filters_and_tags()

        for entry in get_command_output(f"{self._source.value} get pods -A -o custom-columns=:metadata.namespace,:metadata.name"):
            try:
                namespace, pod_name = entry.split()
            except ValueError:
                continue
            if namespace in self._namespaces:
                namespace_directory = Path(self._logs_location, namespace)
                namespace_directory.mkdir(parents=True, exist_ok=True)

                yield LogFile(
                    path=Path(namespace_directory, pod_name),
                    content=get_command_output(f"{self._source.value} logs {pod_name} -n {namespace} {filters}"),
                    regexes=self._regexes,
                    tags=tags
                )

    def _prepare_filters_and_tags(self):
        filters = ""
        tags = ""

        if self._since:
            filters = f"--since={self._since}"
        elif self._since_time:
            filters = f"--since-time={self._since_time}"
        if self._previous:
            filters = f"{filters} --previous"
            tags = ".previous"
        return filters, tags
