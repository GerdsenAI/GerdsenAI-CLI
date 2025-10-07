# Azure-Specific Coding Instructions

⚠️ **IMPORTANT**: These instructions should **ONLY** be applied when the user is explicitly working with Azure resources, services, or deployments. Do not apply these rules for general application development.

---

## 🔧 When to Use These Instructions

Apply these instructions when the user mentions or is working with:
- Azure Functions
- Azure Static Web Apps
- Azure App Service
- Azure Storage
- Azure Cosmos DB
- Any other Azure services
- Deploying to Azure
- Azure infrastructure as code (Bicep, ARM templates)

**Do NOT apply** these instructions for:
- Local development
- Non-Azure cloud platforms (AWS, GCP, etc.)
- General Python/JavaScript/TypeScript development
- Database work not involving Azure Cosmos DB
- Storage operations not involving Azure Storage

---

## Azure Tools Usage Rules

### Rule 1: Use Azure Tools
When handling requests related to Azure, always use your Azure-specific tools if available.

### Rule 2: Azure Code Generation Best Practices
Before generating code for Azure, running terminal commands for Azure, or performing operations related to Azure:
- Invoke the `get_bestpractices` tool if available
- Call it with `resource = "general"` and `action = "code-generation"`
- Apply the returned best practices to your code generation

### Rule 3: Azure Deployment Best Practices
Before deploying to Azure or preparing applications for Azure deployment:
- Invoke the `get_bestpractices` tool if available
- Call it with `resource = "general"` and `action = "deployment"`
- Follow the deployment guidelines provided

### Rule 4: Azure Functions Code Generation
Before generating code for Azure Functions or performing Azure Functions operations:
- Invoke the `get_bestpractices` tool if available
- Call it with `resource = "azurefunctions"` and `action = "code-generation"`
- Follow Azure Functions-specific patterns and best practices

### Rule 5: Azure Functions Deployment
Before deploying Azure Functions apps or preparing for deployment:
- Invoke the `get_bestpractices` tool if available
- Call it with `resource = "azurefunctions"` and `action = "deployment"`
- Ensure proper configuration and resource setup

### Rule 6: Azure Static Web Apps
Before working with Azure Static Web Apps:
- Choose the most relevant Azure best practice tool based on its description
- Follow SWA-specific deployment and configuration patterns

### Rule 7: Plan Before Editing (Azure Web Apps)
When generating code for Azure Functions and Azure Static Web Apps:
1. **Always create a plan** and explain it to the user first
2. **Wait for user consent** before making any file changes
3. Show what files will be modified and why
4. Explain any Azure-specific configuration changes

### Rule 8: Summarize Before Action (Azure Functions)
When the user asks about Azure Functions:
- Invoke the `azure_development-summarize_topic` tool first (if available)
- Check if any existing custom mode could be a good fit
- Suggest the most appropriate approach before proceeding

---

## 📋 Best Practices Summary

### Security
- Never hardcode credentials or connection strings
- Always use Azure Key Vault for secrets
- Use managed identities when possible
- Follow principle of least privilege for permissions

### Performance
- Use appropriate service tiers for workload
- Implement caching where beneficial
- Consider regional deployment for latency
- Monitor and optimize resource usage

### Cost Optimization
- Choose appropriate consumption vs. dedicated plans
- Implement auto-scaling policies
- Clean up unused resources
- Use reserved instances for predictable workloads

### Reliability
- Implement retry policies for transient failures
- Use health checks and monitoring
- Design for regional redundancy
- Maintain deployment slots for zero-downtime updates

---

## 🚫 What NOT to Do

1. **Don't apply Azure patterns** to non-Azure code
2. **Don't assume Azure deployment** unless explicitly stated
3. **Don't add Azure SDK dependencies** unless working on Azure code
4. **Don't use Azure-specific environment variables** in local development
5. **Don't overcomplicate** local development with Azure-specific concerns

---

## ✅ Activation Checklist

Before applying these instructions, verify:
- [ ] User explicitly mentioned Azure
- [ ] Task involves Azure services or deployment
- [ ] Azure-specific tools are available
- [ ] User confirmed they're deploying to Azure

If any of these are unclear, **ask the user first** before applying Azure-specific patterns.
