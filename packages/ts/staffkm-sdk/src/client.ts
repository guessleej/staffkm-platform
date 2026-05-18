import axios, { AxiosInstance } from 'axios'
import { AuthResource } from './resources/auth'
import { WorkspacesResource } from './resources/workspaces'
import { KnowledgeResource } from './resources/knowledge'
import { ApplicationsResource } from './resources/applications'
import { ChatResource } from './resources/chat'
import { QuotaResource } from './resources/quota'
import { BillingResource } from './resources/billing'
import { PluginsResource } from './resources/plugins'

export interface StaffKMOptions {
  baseURL: string
  apiKey?: string
  token?: string
  workspaceId?: string
  timeout?: number
}

export class StaffKM {
  private http: AxiosInstance
  workspaceId?: string

  auth: AuthResource
  workspaces: WorkspacesResource
  knowledge: KnowledgeResource
  applications: ApplicationsResource
  chat: ChatResource
  quota: QuotaResource
  billing: BillingResource
  plugins: PluginsResource

  constructor(opts: StaffKMOptions) {
    if (!opts.apiKey && !opts.token) {
      throw new Error('must provide either apiKey or token')
    }
    const headers: Record<string, string> = {}
    if (opts.apiKey) headers['X-API-Key'] = opts.apiKey
    if (opts.token) headers['Authorization'] = `Bearer ${opts.token}`
    if (opts.workspaceId) headers['X-Workspace-ID'] = opts.workspaceId

    this.http = axios.create({
      baseURL: opts.baseURL.replace(/\/$/, ''),
      timeout: opts.timeout || 30000,
      headers,
    })
    this.workspaceId = opts.workspaceId

    this.auth = new AuthResource(this.http)
    this.workspaces = new WorkspacesResource(this.http)
    this.knowledge = new KnowledgeResource(this.http)
    this.applications = new ApplicationsResource(this.http)
    this.chat = new ChatResource(this.http)
    this.quota = new QuotaResource(this.http)
    this.billing = new BillingResource(this.http)
    this.plugins = new PluginsResource(this.http)
  }
}
