# Exporting your data

Account owners can export all projects, comments and attachments as a ZIP archive. Start an export from Settings, Data, Export. Large accounts are processed in the background and the download link arrives by e-mail when the archive is ready.

Export links stay valid for seven days. Each archive contains one JSON file per project and the original attachment files in an `attachments` folder.

Exports can also be started through the API with `POST /exports`; poll `GET /exports/{id}` until its status is `ready`. A read-only token is enough to download an export.
