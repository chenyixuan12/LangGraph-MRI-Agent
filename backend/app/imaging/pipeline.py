from pathlib import Path


class SuperResolutionPipeline:
    """Model adapter boundary. The baseline keeps the API demonstrable and replaceable."""

    SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    def run(self, input_path: Path, output_path: Path, scale: int, method: str = "baseline") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if input_path.suffix.lower() not in self.SUPPORTED_IMAGE_TYPES:
            raise ValueError("当前占位管线仅支持 PNG/JPEG/TIFF/BMP；请在 imaging 适配器中接入 DICOM/NIfTI 模型。")
        from PIL import Image

        with Image.open(input_path) as image:
            width, height = image.size
            # Lanczos is a deterministic baseline; replace this branch with a trained MRI model.
            result = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
            result.save(output_path)
        return output_path
