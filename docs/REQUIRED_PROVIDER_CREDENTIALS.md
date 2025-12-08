# Required Provider Credentials & Configuration

This document serves as the authoritative registry for all GPU provider integrations supported by GPUBROKER. It details the specific credentials, environment variables, and configuration data required to enable "Real Implementation" connections for each provider.

> **Note:** All environment variables should be added to your `.env` file (local) or your Secrets Manager (production). Do not commit these values to source control.

## 1. Primary Cloud Providers (Hyperscalers)

These providers typically require OAuth2 service account credentials or CLI configuration files.

| Provider | Env Variable / Config | Required Data | How to Acquire |
| :--- | :--- | :--- | :--- |
| **AWS SageMaker** | `AWS_ACCESS_KEY_ID`<br>`AWS_SECRET_ACCESS_KEY`<br>`AWS_REGION` | IAM User Credentials | AWS Console -> IAM -> Users -> Security credentials. Ensure `AmazonSageMakerFullAccess`. |
| **Google Vertex AI** | `GOOGLE_APPLICATION_CREDENTIALS` | Path to JSON Key File | GCP Console -> IAM & Admin -> Service Accounts -> Create Key (JSON). |
| **Azure ML** | `AZURE_CLIENT_ID`<br>`AZURE_CLIENT_SECRET`<br>`AZURE_TENANT_ID`<br>`AZURE_SUBSCRIPTION_ID` | Service Principal Config | Azure Portal -> App Registrations -> Certificates & secrets. |
| **Oracle OCI** | `OCI_USER_OCID`<br>`OCI_TENANCY_OCID`<br>`OCI_FINGERPRINT`<br>`OCI_KEY_FILE` | API Signing Key | OCI Console -> User Settings -> API Keys -> Add API Key. |
| **Alibaba Cloud** | `ALIBABA_ACCESS_KEY_ID`<br>`ALIBABA_ACCESS_KEY_SECRET` | RAM User Key | Alibaba Cloud Console -> RAM -> Users -> Create AccessKey. |
| **Tencent Cloud** | `TENCENT_SECRET_ID`<br>`TENCENT_SECRET_KEY` | CAM User Key | Tencent Cloud Console -> CAM -> API Key Management. |

## 2. Specialized GPU Clouds

These providers offer direct GPU rental and typically use a simple API Key or Bearer Token.

| Provider | Env Variable | Required Data | How to Acquire |
| :--- | :--- | :--- | :--- |
| **RunPod** | `RUNPOD_API_KEY` | API Key | RunPod Settings -> API Keys. |
| **Vast.ai** | `VASTAI_API_KEY` | API Key | Vast.ai Console -> Account -> API Key (Get API Key). |
| **CoreWeave** | `COREWEAVE_API_KEY` | Kubernetes Token / API Key | Cloud config file (`kubeconfig`) or API token from CoreWeave Cloud. |
| **Lambda Labs** | `LAMBDALABS_API_KEY` | API Key | Lambda Cloud -> Settings -> API Keys. |
| **Paperspace** | `PAPERSPACE_API_KEY` | API Key | Paperspace Console -> Team Settings -> API Keys. |
| **FluidStack** | `FLUIDSTACK_API_KEY` | API Key | FluidStack Console -> API Keys. |
| **Jarvis Labs** | `JARVIS_API_KEY` | API Key | Jarvis Labs Dashboard -> Tokens. |

## 3. Serverless Inference & AI Platforms

Providers focused on model serving and inference endpoints.

| Provider | Env Variable | Required Data | How to Acquire |
| :--- | :--- | :--- | :--- |
| **HuggingFace** | `HUGGINGFACE_API_KEY` | User Access Token | HuggingFace Settings -> Access Tokens (Read/Write). |
| **Replicate** | `REPLICATE_API_TOKEN` | API Token | Replicate Dashboard -> Account -> API Token. |
| **DeepInfra** | `DEEPINFRA_API_KEY` | API Key | DeepInfra Dashboard -> API Keys. |
| **Groq** | `GROQ_API_KEY` | API Key | Groq Cloud Console -> API Keys. |
| **Cerebras** | `CEREBRAS_API_KEY` | API Key | Cerebras Cloud -> Developer Settings. |
| **Scale AI** | `SCALEAI_API_KEY` | API Key | Scale AI Dashboard -> Settings -> API Keys. |
| **Run:AI** | `RUNAI_CLIENT_ID`<br>`RUNAI_CLIENT_SECRET` | Client Credentials | Run:AI Administrator Console -> Application -> Create Client. |
| **Together AI** | `TOGETHER_API_KEY` | API Key | Together AI Settings -> API Keys. |
| **Fireworks AI** | `FIREWORKS_API_KEY` | API Key | Fireworks AI Console -> API Keys. |

## 4. Academic & Research Platforms

| Provider | Env Variable | Required Data | How to Acquire |
| :--- | :--- | :--- | :--- |
| **Kaggle** | `KAGGLE_USERNAME`<br>`KAGGLE_KEY` | `kaggle.json` values | Kaggle Profile -> Settings -> Create New API Token. |
| **IBM Watson** | `IBM_WATSON_API_KEY`<br>`IBM_WATSON_URL` | IAM API Key | IBM Cloud -> Resource List -> Watson Service -> Service Credentials. |
| **Spell** | `SPELL_TOKEN` | Auth Token | Spell CLI (`spell login`) or Dashboard Settings. |
| **NVIDIA DGX Cloud** | `NVIDIA_NGC_API_KEY` | NGC API Key | NVIDIA NGC Portal -> Setup -> Get API Key. |

---

## 3. Integration Checklist for Developers

When implementing a new adapter from this list:

1.  **Registry:** Ensure the provider key (e.g., `runpod`, `vastai`) is added to `backend/provider-service/core/registry.py`.
2.  **Env Loading:** Ensure `backend/provider-service/config.py` (or equivalent) loads the specific Env Variable listed above.
3.  **Authentication:** Use the standard `BaseProviderAdapter.validate_credentials` method to check these keys.
4.  **No Mocking:** If you do not have a real key, do **not** commit fake data. Use the `Vast.ai` public adapter pattern if possible, or mark the provider as "Coming Soon" in the UI.
