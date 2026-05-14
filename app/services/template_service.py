"""HTML template loading."""

import os


class TemplateService:
    def __init__(self, template_dir: str):
        self.template_dir = template_dir

    def load(self, filename: str) -> str:
        with open(os.path.join(self.template_dir, filename), "r", encoding="utf-8") as file:
            return file.read()
