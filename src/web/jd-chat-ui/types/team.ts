export type TeamRole = 'owner' | 'admin' | 'member';

export interface TeamMember {
  id: number;
  user_id: number;
  username: string;
  email: string;
  role: TeamRole;
  joined_at: string;
}

export interface Team {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  owner_username: string;
  member_count: number;
  created_at: string;
  members?: TeamMember[];
}

export interface TeamInvitation {
  id: number;
  team_id: number;
  code: string;
  role: TeamRole;
  created_by: number;
  expires_at: string;
  is_used: boolean;
  used_by: number | null;
}

export interface CreateTeamRequest {
  name: string;
  description?: string;
}

export interface CreateInvitationRequest {
  role: TeamRole;
}

export interface JoinTeamRequest {
  invitation_code: string;
}

export interface UpdateMemberRoleRequest {
  member_id: number;
  role: TeamRole;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
