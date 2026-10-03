# CI 签名密钥

本 App（`zzy.dsha.Kotlin`）用一把固定的 CI 密钥签名。**换密钥等于换 App 身份**：Android 只允许
同签名覆盖安装，换了之后已安装的用户只能卸载重装、App 数据会丢。

- 证书 SHA-256：`79:77:DF:F4:D4:52:C3:90:8D:AA:EA:91:F0:A2:0B:1A:BA:71:18:1B:73:4B:A4:3A:B5:48:98:FF:1E:31:42:8F`
- 别名 `dsha-ci`，PKCS12，4096 位 RSA，有效期到 2054-02-18
  （Android 要求证书有效期覆盖应用生命周期，不要用 1 年的短期证书）
- store 密码与 key 密码相同

## 仓库 Secrets

| Secret | 值 |
|---|---|
| `DSHA_CI_KEYSTORE_B64` | `base64 -w0 dsha-kotlin-ci.keystore` 的输出 |
| `DSHA_CI_KEYSTORE_PASSWORD` | 密钥库密码 |

两个 Secret 缺失时，工作流会现场生成一把临时密钥并给出警告。那样的包每次构建签名都不同，
**不能发版，也不能覆盖升级**。

## 加密备份

`dsha-kotlin-ci-signing.tar.enc` 已生成，内容是一把密钥库与它的密码文件：

- `dsha-kotlin-ci.keystore`（PKCS12，alias `dsha-ci`）
- `pass.txt`（密钥库密码）

加密：OpenSSL AES-256-CBC，PBKDF2-SHA256，600000 次迭代，随机盐。
**口令不在仓库、也不在 Secrets**，由仓库所有者离线保管（生成时放在仓库外的
`signing/secrets/backup-passphrase.txt`，请自行复制到安全位置后从工作目录删除）。


恢复（会提示输入口令）：

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 \
  -in .github/signing/dsha-kotlin-ci-signing.tar.enc | tar -xf -
```

解出来先核对证书指纹与上面那串一致：

```bash
keytool -list -v -keystore dsha-kotlin-ci.keystore -storepass "$(cat pass.txt)" | grep SHA256
```

再写回 Secrets，最后删掉解密出的密钥库和密码文件。

## 注意

- `.github/signing/dsha-ci-signing.tar.enc` 是**旧 App `zzy.dsha.com` 的密钥备份**，与本 App 无关，
  保留只为不丢历史（原仓库 `DSHA-zzy` 里也有同一份）。**不要**拿它当本 App 的密钥。
- 私钥不要提交进仓库，也不要贴到对话/Issue 里。
