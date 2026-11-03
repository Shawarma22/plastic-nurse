from pathlib import Path
from typing import Dict, List, Union
import yaml
from app.schemas.protocol import ProtocolSchema, StepType


class ProtocolValidationError(Exception):
    def __init__(self, errors: List[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class ProtocolParser:
    @staticmethod
    def parse_string(yaml_content: str) -> ProtocolSchema:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ProtocolValidationError(["Protocol YAML root must be a mapping"])
        schema = ProtocolSchema(**data)
        errors = ProtocolParser.validate(schema)
        if errors:
            raise ProtocolValidationError(errors)
        return schema

    @staticmethod
    def parse_file(file_path: Union[str, Path]) -> ProtocolSchema:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Protocol file not found: {path}")
        content = path.read_text(encoding="utf-8")
        return ProtocolParser.parse_string(content)

    @staticmethod
    def validate(schema: ProtocolSchema) -> List[str]:
        errors: List[str] = []
        step_ids = {s.id for s in schema.steps}

        if len(step_ids) != len(schema.steps):
            errors.append("Duplicate step IDs detected in protocol definition")

        if schema.initial_step not in step_ids:
            errors.append(f"Initial step '{schema.initial_step}' not found in defined steps")

        for s in schema.steps:
            if s.default_next and s.default_next not in step_ids:
                errors.append(f"Step '{s.id}' default_next '{s.default_next}' does not exist")

            if s.type == StepType.MEASURE and not s.target_vital:
                errors.append(f"Measure step '{s.id}' must specify target_vital")

            if s.type == StepType.DISPENSE and not s.item_id:
                errors.append(f"Dispense step '{s.id}' must specify item_id")

            if s.type == StepType.WAIT and (s.duration_sec is None or s.duration_sec <= 0):
                errors.append(f"Wait step '{s.id}' must have duration_sec > 0")

            if s.type == StepType.BRANCH:
                if not s.conditions:
                    errors.append(f"Branch step '{s.id}' must define at least one condition")
                else:
                    for cond in s.conditions:
                        if cond.target_step not in step_ids:
                            errors.append(f"Branch step '{s.id}' target '{cond.target_step}' does not exist")

        return errors

    @staticmethod
    def load_directory(dir_path: Union[str, Path]) -> Dict[str, ProtocolSchema]:
        directory = Path(dir_path)
        protocols: Dict[str, ProtocolSchema] = {}
        if not directory.exists() or not directory.is_dir():
            return protocols

        for ext in ("*.yaml", "*.yml"):
            for file_path in directory.glob(ext):
                try:
                    proto = ProtocolParser.parse_file(file_path)
                    protocols[proto.metadata.id] = proto
                except Exception as e:
                    raise ProtocolValidationError([f"Failed to load {file_path.name}: {e}"])

        return protocols


protocol_parser = ProtocolParser()
