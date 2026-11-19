> **Обновление v0.31.0:** автоматическая сборка через GitHub Actions описана в `GITHUB_ACTIONS_SETUP_RU.md`. Ниже — предыдущий порядок **ручной** публикации v0.30.0, сохранённый для справки.

# SnowRunner Helper v0.30.0 — GitHub OTA

Подтверждённый репозиторий: https://github.com/FASBER/SnowRunner-Helper (публичный, ветка main).

**Важно:** GitHub Releases пока пуст. `Setup.exe` не собран, публичный ключ Ed25519 не задан. Поэтому OTA безопасно отключён; наличие URL не означает, что обновления работают.

## Один раз перед самым первым Windows-релизом

1. На доверенном Windows-компьютере запустите `python release_tools\generate_key.py D:\Secrets\snowrunner_ed25519.pem`. Не храните закрытый ключ в проекте, GitHub, облачных workflow и не передавайте его через чат.
2. Генератор покажет **публичный** Ed25519 ключ (base64); добавьте только его в `PUBLIC_KEY_ED25519_BASE64` в файле `update_config.py`. Адрес `FASBER/SnowRunner-Helper` уже настроен.
3. Соберите EXE и установщик с этим публичным ключом через `build_installer_windows.bat` (Windows, Python, Inno Setup 6). Сохраните стабильный AppId и отдельную папку профилей.
4. Протестируйте установку и запуск, выбор пути, обновление и сохранность профилей на настоящей Windows. Начальную сборку нужно установить вручную.

## Для каждого нового релиза

1. Повышайте версию согласованно в `version.json`, `setup_snowrunner.iss`, `build_installer_windows.bat` и конфигурации сборки. Не меняйте существующие теги и release assets.
2. Подпишите Windows EXE сертификатом Authenticode, если есть. После последней модификации EXE создайте Ed25519 `update.json`:

   ```bat
   python release_tools\prepare_github_release.py FASBER SnowRunner-Helper 0.30.0 installer_build\SnowRunnerHelper_Setup_v0.30.0.exe D:\Secrets\snowrunner_ed25519.pem --notes "Первый релиз" --output update.json
   ```

3. В https://github.com/FASBER/SnowRunner-Helper/releases/new создайте **обычный** релиз с тегом `v0.30.0` и приложите два файла: `SnowRunnerHelper_Setup_v0.30.0.exe`, `update.json`. Для первой публикации не выбирайте prerelease/draft.
4. Приложение читает `https://github.com/FASBER/SnowRunner-Helper/releases/latest/download/update.json`. Проверяет цифровую подпись Ed25519, версию, канал, размер и SHA-256 EXE. Предлагает обновить с подтверждением пользователя.

**Не загружайте** приватный PEM, игровые сохранения, закрытые игровые архивы или оригинальные файлы игры. Описание публичного релиза и лицензирование отдельных медиа-ресурсов нужно проверять до публикации.
