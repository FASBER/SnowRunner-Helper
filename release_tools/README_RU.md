**Для GitHub Releases вместо собственного сервера используйте `GITHUB_RELEASES_RU.md`.**

# Публикация подписанного OTA-релиза

1. Только на доверенном компьютере хранителя ключей: `python release_tools/generate_key.py D:\\Secrets\\snowrunner_signing.pem`. Секретный файл НЕ помещать в ZIP, Git или приложение. Хранить резервную копию ключа в безопасном хранилище.
2. В `update_config.py` занести выведенный PUBLIC key и HTTPS URL опубликованного файла `manifest.json`; только затем собрать Windows EXE и установщик. Приватный ключ нужен только автору релизов.
3. Сборка: `build_installer_windows.bat` → `installer_build\\SnowRunnerHelper_Setup_v27.exe`. Подписать установщик Authenticode для доверия Windows, если есть сертификат. Ed25519 манифест не заменяет Authenticode.
4. Выгрузить этот EXE на постоянный HTTPS адрес, проверить что файл скачивается без изменения байтов.
5. Создать подписанный манифест из ТОЧНО этого EXE: `python release_tools/sign_release.py D:\\Secrets\\snowrunner_signing.pem installer_build\\SnowRunnerHelper_Setup_v27.exe https://your-domain.example/downloads/SnowRunnerHelper_Setup_v27.exe 0.27.0 manifest.json`.
6. Опубликовать `manifest.json` по URL из шага 2. Только после этого приложение начнёт предлагать OTA-обновления, версии должны быть строго выше установленной.
7. Произвести полный тест установки/обновления и отката на Windows 10/11 с реальными профилями. **Сервер и закрытый ключ пока не настроены; в собранном проекте OTA отключено по умолчанию.**

Манифест содержит `payload` с полями `version`, `channel`, `url`, `sha256`, `size`, `notes`, а также `signature` (Ed25519 в base64) над каноническим JSON `payload`. Нельзя редактировать манифест после подписи.
