# Messages

Every message the SDK produces, from the help text of each setting to the problems found in an ad, lives in `tapaz_sdk/messages.yaml`. Nothing is hardcoded, so you can replace any of them, for example to show the form errors to your users in Azerbaijani.

## Replace a few

```python
from tapaz_sdk import messages

messages.use({
    "ad.required": "'{name}' mütləqdir",
    "ad.price": "bu kateqoriyada qiymət mütləqdir",
    "ad.photos": "bu kateqoriyada ən azı bir şəkil lazımdır",
})
```

Keys are dotted paths in the YAML file. A nested mapping works too: `{"ad": {"price": "..."}}`.

## Load a file

```yaml
ad:
  required: "'{name}' mütləqdir"
  between: "'{name}' {low} ilə {high} arasında olmalıdır"
  price: bu kateqoriyada qiymət mütləqdir
error:
  session: tap.az sessiyanı qəbul etmir, yenidən daxil olun
```

```python
messages.use("messages.az.yaml")
```

## Rules

- An unknown key raises `KeyError`, so a typo fails at once.
- Keep the `{placeholders}`; they are filled with `str.format`.
- The change applies to the whole process.
- `messages.reset()` restores the defaults.

## Every key

```python
for key, text in sorted(messages.catalog().items()):
    print(key, "=", text)
```

| Group | Used for |
| --- | --- |
| `settings.*` | The description of each setting |
| `value.*` | Arguments refused before sending |
| `ad.*` | Problems found when an ad is checked against its category |
| `error.*` | Errors from tap.az, the photo service, the login service and the network |
| `note.*` | Notes such as the one in `CodeSent.note` |

`messages.text(key, **params)` returns one message with its placeholders filled. The default file: [src/tapaz_sdk/messages.yaml](https://github.com/qiyascc/tapaz-python-sdk/blob/main/src/tapaz_sdk/messages.yaml).
