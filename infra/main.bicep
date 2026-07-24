// infra/main.bicep
// Azure Agent Blueprint — production infrastructure (Gold-Path pattern from
// azure-finops-agent / foundry-agent-webapp / get-started-with-ai-agents).
// Deploys: Resource Group, Log Analytics + App Insights, Container App (agent runtime),
// Managed Identity, and an Azure OpenAI (or Foundry) endpoint slot.

targetScope = 'subscription'

param location string = 'eastus'
param environment string = 'dev'
param appName string = 'azure-agent-blueprint'
param openAiEndpoint string = ''   // set via azd env or pipeline
param openAiDeployment string = 'gpt-4o'

var rgName = '${appName}-${environment}-rg'
var lawName = '${appName}-${environment}-law'
var aiName = '${appName}-${environment}-ai'
var caEnvName = '${appName}-${environment}-cae'
var caName = '${appName}-${environment}-ca'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
}

resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  resourceGroup: rgName
  properties: { sku: { name: 'PerGB2018' } }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  resourceGroup: rgName
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: caEnvName
  location: location
  resourceGroup: rgName
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: law.customerId, sharedKey: law.primarySharedKey }
    }
  }
}

resource mi 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-${environment}-mi'
  location: location
  resourceGroup: rgName
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: caName
  location: location
  resourceGroup: rgName
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${mi.id}': {} } }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: contains(openAiEndpoint, 'key') ? {} : {}
      ingress: { external: true, targetPort: 8000, transport: 'http' }
    }
    template: {
      containers: [{
        name: 'agent'
        image: 'mcr.microsoft.com/azure-agent-blueprint:latest'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'APPINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
          { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeployment }
        ]
      }]
    }
  }
}

output appInsightsConnectionString string = appInsights.properties.ConnectionString
output containerAppUrl string = containerApp.properties.configuration.ingress.fqdn
output principalId string = mi.properties.principalId
