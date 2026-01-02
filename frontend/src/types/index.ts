export interface Server {
  id: number;
  name: string;
  hostname: string;
  port: number;
  username: string;
  ssh_key_path?: string;
  os_type: 'debian' | 'almalinux';
  last_check?: string;
  updates_available: number;
  status: 'online' | 'offline' | 'updating' | 'unknown';
  created_at: string;
}

export interface User {
  id: number;
  username: string;
  email?: string;
  is_admin: boolean;
  is_active: boolean;
  auth_type: 'local' | 'ldap';
  created_at: string;
  last_login?: string;
}

export interface UpdateHistory {
  id: number;
  server_id: number;
  server_name: string;
  server_hostname: string;
  action: 'check' | 'update' | 'security_update' | 'reboot' | 'error';
  update_type: 'all' | 'security';
  packages_count: number;
  package_list: Package[];
  output: string;
  success: boolean;
  duration?: number;
  created_at: string;
}

export interface Package {
  name: string;
  version?: string;
  old_version?: string;
  new_version?: string;
  is_security?: boolean;
}

export interface Schedule {
  id: number;
  server_id: number;
  server_name: string;
  enabled: boolean;
  schedule_type: 'daily' | 'weekly' | 'monthly';
  day_of_week?: number;
  day_of_month?: number;
  hour: number;
  minute: number;
  update_type: 'all' | 'security';
  auto_reboot: boolean;
  created_at: string;
  updated_at: string;
}

export interface Stats {
  total_servers: number;
  servers_with_updates: number;
  total_updates: number;
  servers_online: number;
  servers_offline: number;
  servers_updating: number;
  servers_debian: number;
  servers_almalinux: number;
  total_schedules: number;
  enabled_schedules: number;
  updates_last_24h: number;
  recent_activity: UpdateHistory[];
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  redirect?: string;
}

export interface ProvisioningStep {
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  message?: string;
  error?: string;
}

export interface ProvisionRequest {
  name: string;
  hostname: string;
  port: number;
  root_username: string;
  root_password: string;
  os_type: 'debian' | 'almalinux';
}

export interface ProvisionResponse {
  success: boolean;
  message: string;
  server?: Server;
  provisioning_steps?: ProvisioningStep[];
  error?: string;
  details?: string;
}

export interface SSHKeyInfo {
  exists: boolean;
  private_key_path?: string;
  public_key_path?: string;
  fingerprint?: string;
  created?: number;
  public_key?: string;
  message?: string;
}
