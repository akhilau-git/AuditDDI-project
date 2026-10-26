# Applying the seven-source code update in Colab

The working code changes are local to this checkout. Until they are pushed to
GitHub, apply the packaged ZIP to the existing `/content/auditddi` clone.

```python
from google.colab import files
from pathlib import Path
from zipfile import ZipFile

uploaded = files.upload()  # select auditddi_seven_source_colab_update.zip
archive = Path('/content') / next(iter(uploaded))
with ZipFile(archive) as bundle:
    bundle.extractall('/content/auditddi')
```

Then mount Drive, set `AUDITDDI_DATA_BASE` and `AUDITDDI_RESULTS_BASE`, and
follow section 11.1 of `AUDITDDI_METHODOLOGY_AND_WORKFLOW.md`.

The ZIP contains only the files needed for the updated source preparation,
ChEMBL pretraining, multimodal training, and local inference path. It does not
copy or change any dataset files.
