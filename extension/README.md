# nes_recycle browser extension

Chrome、Edge、Safari Web Extension 向けの回収フォーム入力補助です。

## できること

- `https://input-form.jp/modules/nespresso_recyclingathome/` の入力画面に保存済みプロフィールを入力する
- 回収希望日、時間帯、カプセル種類、バッグ数を既定値またはポップアップ指定値で入力する
- ブラウザ標準の自動入力候補が出やすいように、一部フィールドへ `autocomplete` / `inputmode` 属性を補う

確認画面への遷移や本送信は自動実行しません。

## 保存先

プロフィールと既定値は WebExtension の `storage.local` に保存します。ブラウザプロファイル内のローカル保存で、Chrome / Edge / Safari 間では共有されません。

保存される項目:

- ネスプレッソのお客様番号
- 姓・名
- 郵便番号
- 回収先住所
- 電話番号
- メールアドレス
- カプセル種類、回収希望日、時間帯、バッグ数の既定値
- フォーム表示時に自動入力するかどうか

## Chrome / Edge での読み込み

1. `chrome://extensions/` または `edge://extensions/` を開く
2. デベロッパーモードを有効にする
3. 「パッケージ化されていない拡張機能を読み込む」でこの `extension/` ディレクトリを選択する
4. 拡張機能の「設定」からプロフィールを保存する

## Chrome / Edge 向け配布zip

リポジトリルートで次を実行します。

```sh
make extension-package
```

`dist/nes_recycle_extension-<version>.zip` が生成されます。このzipはmanifestをルートに持つため、Chrome Web Store / Microsoft Edge Add-ons のアップロード用として使えます。

## Safari での読み込み

Safari は WebExtension を Safari App Extension としてラップする必要があります。

```sh
xcrun safari-web-extension-converter extension
```

生成されたXcodeプロジェクトを開き、署名設定を行って実行します。Windows版Safariは現行サポート対象外のため、この実装のSafari対象はmacOS版です。

リポジトリ側の既定設定でXcodeプロジェクトを生成する場合は、ルートで次を実行します。

```sh
make safari-project
```

生成先は `build/safari/` です。Safari向け配布にはApple Developer Programの署名設定と、App Store配布またはDeveloper ID配布の手続きが必要です。

Apple Developer Team IDはKeychainから自動取得します。既定では `st.rio.nes_recycle` / `safari_development_team_id` のgeneric passwordを先に読み、なければKeychain上の `Developer ID Application` code signing identityからTeam IDを取得します。

```sh
make safari-project
```

Team IDを明示する場合:

```sh
make safari-project SAFARI_DEVELOPMENT_TEAM=ABCDE12345
```

Apple Development証明書側のTeam IDを使う場合:

```sh
make safari-project SAFARI_CODESIGN_IDENTITY="Apple Development"
```

generic passwordとして保存する場合:

```sh
security add-generic-password -U -s st.rio.nes_recycle -a safari_development_team_id -w ABCDE12345
```

Team IDを取得できた場合、生成後のXcodeプロジェクトへ `DEVELOPMENT_TEAM`、`CODE_SIGN_STYLE`、`MARKETING_VERSION`、`CURRENT_PROJECT_VERSION` を反映します。Team IDを取得できない場合はTeam IDを設定せず、ローカル確認用のプロジェクトだけを生成します。

Bundle Identifierを変える場合:

```sh
make safari-project SAFARI_BUNDLE_IDENTIFIER=com.example.nesrecycle
```

署名方式やバージョンを明示する場合:

```sh
make safari-project \
  SAFARI_DEVELOPMENT_TEAM=ABCDE12345 \
  SAFARI_CODE_SIGN_STYLE=Automatic \
  SAFARI_MARKETING_VERSION=0.1.0 \
  SAFARI_CURRENT_PROJECT_VERSION=1
```
