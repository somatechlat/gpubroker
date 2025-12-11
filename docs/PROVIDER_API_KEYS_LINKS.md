# 🔑 Provider API Keys - Direct Links

This document provides direct links to obtain API keys for all 30+ GPU providers supported by GPUBROKER.

---

## �  API Keys Status Summary (December 8, 2024)

| # | Provider | Status | API Key (truncated) | API Base URL |
|---|----------|--------|---------------------|--------------|
| 1 | AWS SageMaker | ✅ | `AKIAUM7X...` | `https://runtime.sagemaker.us-east-1.amazonaws.com` |
| 2 | Google Vertex AI | ✅ | `AIzaSyD8...` | `https://us-central1-aiplatform.googleapis.com` |
| 3 | Azure ML | ❌ | – | `https://management.azure.com` |
| 4 | Oracle OCI | ❌ | – | `https://iaas.us-ashburn-1.oraclecloud.com` |
| 5 | Alibaba Cloud | ❌ | – | `https://ecs.aliyuncs.com` |
| 6 | Tencent Cloud | ❌ | – | `https://cvm.tencentcloudapi.com` |
| 7 | RunPod | ✅ | `rpa_VY740...` | `https://api.runpod.io/graphql` |
| 8 | Vast.ai | ✅ | `62546715...` | `https://console.vast.ai/api/v0` |
| 9 | CoreWeave | ❌ | – | `https://api.coreweave.com` |
| 10 | Lambda Labs | ❌ | – | `https://cloud.lambdalabs.com/api/v1` |
| 11 | Paperspace | ❌ | – | `https://api.paperspace.io` |
| 12 | HuggingFace | ✅ | `hf_HvhVq...` | `https://api-inference.huggingface.co` |
| 13 | Replicate | ✅ | `r8_HbBY1...` | `https://api.replicate.com/v1` |
| 14 | DeepInfra | ❌ | – | `https://api.deepinfra.com/v1` |
| 15 | Groq | ✅ | `gsk_oty8...` | `https://api.groq.com/openai/v1` |
| 16 | Cerebras | ✅ | `csk-kx3x...` | `https://api.cerebras.ai/v1` |
| 17 | Scale AI | ✅ | `scale_pro...` | `https://api.scale.com/v1` |
| 18 | Together AI | ❌ | – | `https://api.together.xyz/v1` |
| 19 | Fireworks AI | ✅ | `fw_3ZWY2...` | `https://api.fireworks.ai/inference/v1` |
| 20 | Run:AI | ❌ | – | `https://app.run.ai/api/v1` |
| 21 | NVIDIA DGX Cloud | ❌ | – | `https://api.ngc.nvidia.com/v2` |
| 22 | IBM Watson | ❌ | – | `https://us-south.ml.cloud.ibm.com/ml/v4` |
| 23 | Kaggle | ✅ | `KGAT_83c1...` | `https://www.kaggle.com/api/v1` |
| 24 | Salad Cloud | ✅ | `salad_cloud...` | `https://api.salad.com/api/public` |
| 25 | CLORE.ai | ✅ | `CLORE.ai` | `https://api.clore.ai/v1` |
| 26 | RPA | ✅ | `rpa_VY740...` | `https://api.rpa.ai/v1` |
| 27 | RIUNPOND | ✅ | `RIUNPOND` | `https://api.riunpond.io/v1` |
| 28 | Inception | ✅ | `sk_37418...` | `https://api.inception.ai/v1` |
| 29 | OpenRouter | ✅ | `sk-or-v1...` | `https://openrouter.ai/api/v1` |
| 30 | DFB | ✅ | `dfbQ2nzh...` | `https://api.dfb.ai/v1` |

**Summary: 19 providers configured ✅ | 11 providers missing ❌**

> Full keys stored in: `docs/SECRETS_VAULT_KEYS.env` and `docs/provider_api_keys_complete.csv`

---

## 🚀 Quick Setup

1. Click the link for each provider you want to enable
2. Create an account (if needed) and generate an API key
3. Add the key to your `.env` file using the variable name shown
4. Restart the services

---

## Primary Cloud Providers (Hyperscalers)

| # | Provider | Get API Key | Env Variable | Pricing Page |
|---|----------|-------------|--------------|--------------|
| 1 | **AWS SageMaker** | [AWS IAM Console](https://console.aws.amazon.com/iam/home#/security_credentials) | `AWS_ACCESS_KEY_ID`<br>`AWS_SECRET_ACCESS_KEY` | [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) |
| 2 | **Google Vertex AI** | [GCP Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) | `GOOGLE_APPLICATION_CREDENTIALS` | [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing) |
| 3 | **Azure ML** | [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) | `AZURE_CLIENT_ID`<br>`AZURE_CLIENT_SECRET`<br>`AZURE_TENANT_ID` | [Azure ML Pricing](https://azure.microsoft.com/en-us/pricing/details/machine-learning/) |
| 4 | **Oracle OCI** | [OCI API Keys](https://cloud.oracle.com/identity/users) | `OCI_USER_OCID`<br>`OCI_TENANCY_OCID`<br>`OCI_FINGERPRINT` | [OCI GPU Pricing](https://www.oracle.com/cloud/compute/gpu/pricing/) |
| 5 | **Alibaba Cloud** | [Alibaba RAM Console](https://ram.console.aliyun.com/users) | `ALIBABA_ACCESS_KEY_ID`<br>`ALIBABA_ACCESS_KEY_SECRET` | [Alibaba GPU Pricing](https://www.alibabacloud.com/product/gpu/pricing) |
| 6 | **Tencent Cloud** | [Tencent CAM Console](https://console.cloud.tencent.com/cam/capi) | `TENCENT_SECRET_ID`<br>`TENCENT_SECRET_KEY` | [Tencent GPU Pricing](https://intl.cloud.tencent.com/pricing/cvm) |

---

## Specialized GPU Clouds

| # | Provider | Get API Key | Env Variable | Pricing Page |
|---|----------|-------------|--------------|--------------|
| 7 | **RunPod** | [RunPod API Keys](https://www.runpod.io/console/user/settings) | `RUNPOD_API_KEY` | [RunPod Pricing](https://www.runpod.io/gpu-instance/pricing) |
| 8 | **Vast.ai** | [Vast.ai Account](https://cloud.vast.ai/account/) | `VASTAI_API_KEY` | [Vast.ai Pricing](https://vast.ai/pricing) |
| 9 | **CoreWeave** | [CoreWeave Cloud](https://cloud.coreweave.com/) | `COREWEAVE_API_KEY` | [CoreWeave Pricing](https://www.coreweave.com/pricing) |
| 10 | **Lambda Labs** | [Lambda Cloud API](https://cloud.lambdalabs.com/api-keys) | `LAMBDALABS_API_KEY` | [Lambda Pricing](https://lambdalabs.com/service/gpu-cloud#pricing) |
| 11 | **Paperspace** | [Paperspace API Keys](https://console.paperspace.com/account/team/settings) | `PAPERSPACE_API_KEY` | [Paperspace Pricing](https://www.paperspace.com/pricing) |

---

## Serverless Inference & AI Platforms

| # | Provider | Get API Key | Env Variable | Pricing Page |
|---|----------|-------------|--------------|--------------|
| 12 | **HuggingFace** | [HuggingFace Tokens](https://huggingface.co/settings/tokens) | `HUGGINGFACE_API_KEY` | [HF Inference Pricing](https://huggingface.co/pricing) |
| 13 | **Replicate** | [Replicate API Tokens](https://replicate.com/account/api-tokens) | `REPLICATE_API_TOKEN` | [Replicate Pricing](https://replicate.com/pricing) |
| 14 | **DeepInfra** | [DeepInfra Dashboard](https://deepinfra.com/dash/api_keys) | `DEEPINFRA_API_KEY` | [DeepInfra Pricing](https://deepinfra.com/pricing) |
| 15 | **Groq** | [Groq Console](https://console.groq.com/keys) | `GROQ_API_KEY` | [Groq Pricing](https://groq.com/pricing/) |
| 16 | **Cerebras** | [Cerebras Cloud](https://cloud.cerebras.ai/) | `CEREBRAS_API_KEY` | [Cerebras Pricing](https://cerebras.ai/cloud/) |
| 17 | **Scale AI** | [Scale AI Dashboard](https://dashboard.scale.com/settings) | `SCALEAI_API_KEY` | [Scale AI Pricing](https://scale.com/pricing) |
| 18 | **Together AI** | [Together AI Keys](https://api.together.xyz/settings/api-keys) | `TOGETHER_API_KEY` | [Together Pricing](https://www.together.ai/pricing) |
| 19 | **Fireworks AI** | [Fireworks Console](https://fireworks.ai/account/api-keys) | `FIREWORKS_API_KEY` | [Fireworks Pricing](https://fireworks.ai/pricing) |

---

## Enterprise & Research Platforms

| # | Provider | Get API Key | Env Variable | Pricing Page |
|---|----------|-------------|--------------|--------------|
| 20 | **Run:AI** | [Run:AI Console](https://app.run.ai/) | `RUNAI_CLIENT_ID`<br>`RUNAI_CLIENT_SECRET` | [Run:AI Pricing](https://www.run.ai/pricing) |
| 21 | **NVIDIA DGX Cloud** | [NGC Portal](https://ngc.nvidia.com/setup/api-key) | `NVIDIA_NGC_API_KEY` | [DGX Cloud Pricing](https://www.nvidia.com/en-us/data-center/dgx-cloud/) |
| 22 | **IBM Watson** | [IBM Cloud API Keys](https://cloud.ibm.com/iam/apikeys) | `IBM_WATSON_API_KEY`<br>`IBM_WATSON_URL` | [Watson ML Pricing](https://www.ibm.com/cloud/machine-learning/pricing) |
| 23 | **Kaggle** | [Kaggle Account](https://www.kaggle.com/settings/account) | `KAGGLE_USERNAME`<br>`KAGGLE_KEY` | Free (with limits) |

---

## 📋 .env Template

Copy this to your `.env` file and fill in your keys:

```bash
# ============================================
# GPUBROKER - Provider API Keys
# ============================================

# --- Primary Cloud Providers ---
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
AZURE_SUBSCRIPTION_ID=

OCI_USER_OCID=
OCI_TENANCY_OCID=
OCI_FINGERPRINT=
OCI_KEY_FILE=/path/to/oci_api_key.pem

ALIBABA_ACCESS_KEY_ID=
ALIBABA_ACCESS_KEY_SECRET=

TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=

# --- Specialized GPU Clouds ---
RUNPOD_API_KEY=
VASTAI_API_KEY=
COREWEAVE_API_KEY=
LAMBDALABS_API_KEY=
PAPERSPACE_API_KEY=

# --- Serverless Inference ---
HUGGINGFACE_API_KEY=
REPLICATE_API_TOKEN=
DEEPINFRA_API_KEY=
GROQ_API_KEY=
CEREBRAS_API_KEY=
SCALEAI_API_KEY=
TOGETHER_API_KEY=
FIREWORKS_API_KEY=

# --- Enterprise & Research ---
RUNAI_CLIENT_ID=
RUNAI_CLIENT_SECRET=
NVIDIA_NGC_API_KEY=
IBM_WATSON_API_KEY=
IBM_WATSON_URL=
KAGGLE_USERNAME=
KAGGLE_KEY=

# ============================================
# Internal Services
# ============================================
JWT_SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql://gpubroker:gpubroker_dev_password_2024@postgres:5432/gpubroker
REDIS_URL=redis://:redis_dev_password_2024@redis:6379/0
```

---

## ✅ Verification

After adding keys, verify connections:

```bash
# Check provider health
curl http://localhost:${PORT_PROVIDER:-28021}/health

# List configured integrations
curl http://localhost:${PORT_PROVIDER:-28021}/config/integrations

# Test specific provider
curl http://localhost:${PORT_PROVIDER:-28021}/providers?provider=runpod
```

---

## 🔒 Security Notes

1. **Never commit `.env` to git** - It's in `.gitignore`
2. **Use Vault in production** - Store secrets in HashiCorp Vault
3. **Rotate keys regularly** - Set calendar reminders
4. **Use least privilege** - Only grant necessary permissions
5. **Monitor usage** - Set up billing alerts on all providers

---

## 📊 Provider Feature Matrix

| Provider | GPU Types | Regions | Real-time Pricing | Booking API | Compliance |
|----------|-----------|---------|-------------------|-------------|------------|
| RunPod | A100, H100, RTX | US, EU | ✅ GraphQL | ✅ | - |
| Vast.ai | Various | Global | ✅ REST | ✅ | - |
| CoreWeave | A100, H100 | US | ✅ | ✅ | SOC2 |
| Lambda Labs | A100, H100 | US | ✅ | ✅ | - |
| AWS SageMaker | All | Global | ✅ | ✅ | SOC2, HIPAA, GDPR |
| Google Vertex | All | Global | ✅ | ✅ | SOC2, HIPAA, GDPR |
| Azure ML | All | Global | ✅ | ✅ | SOC2, HIPAA, GDPR |
| HuggingFace | Inference | US, EU | ✅ | - | GDPR |
| Replicate | Inference | US | ✅ | - | - |
| Groq | LPU | US | ✅ | - | - |

---

*Last updated: December 2024*
