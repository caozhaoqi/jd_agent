from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import Team, TeamMember, TeamInvitation, TeamRole, InvitationStatus, User
from core.db_auth import get_db_dependency

router = APIRouter()


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    role: str
    joined_at: datetime


class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    member_count: int = 0
    members: List[TeamMemberResponse] = []


class InvitationCreate(BaseModel):
    email: str
    role: str = "member"


class InvitationResponse(BaseModel):
    id: int
    team_id: int
    email: str
    role: str
    status: str
    created_at: datetime
    expires_at: datetime


async def get_current_user_id():
    return 1


@router.get("", response_model=List[TeamResponse])
async def list_teams(
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(Team).join(TeamMember).where(TeamMember.user_id == user_id)
    )
    teams = result.scalars().all()
    
    response = []
    for team in teams:
        member_result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team.id)
        )
        members = member_result.scalars().all()
        
        member_responses = []
        for member in members:
            user_result = await db.execute(
                select(User).where(User.id == member.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            member_responses.append(TeamMemberResponse(
                id=member.id,
                user_id=member.user_id,
                username=user.username if user else None,
                role=member.role.value if isinstance(member.role, TeamRole) else member.role,
                joined_at=member.joined_at
            ))
        
        response.append(TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            owner_id=team.owner_id,
            created_at=team.created_at,
            member_count=len(members),
            members=member_responses
        ))
    
    return response


@router.post("", response_model=TeamResponse)
async def create_team(
    request: TeamCreate,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    team = Team(
        name=request.name,
        description=request.description,
        owner_id=user_id
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    
    owner_member = TeamMember(
        team_id=team.id,
        user_id=user_id,
        role=TeamRole.OWNER
    )
    db.add(owner_member)
    await db.commit()
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        member_count=1,
        members=[TeamMemberResponse(
            id=owner_member.id,
            user_id=user_id,
            username=None,
            role=TeamRole.OWNER.value,
            joined_at=owner_member.joined_at
        )]
    )


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this team")
    
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    member_result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )
    members = member_result.scalars().all()
    
    member_responses = []
    for member in members:
        user_result = await db.execute(
            select(User).where(User.id == member.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        role_value = member.role.value if isinstance(member.role, TeamRole) else member.role
        member_responses.append(TeamMemberResponse(
            id=member.id,
            user_id=member.user_id,
            username=user.username if user else None,
            role=role_value,
            joined_at=member.joined_at
        ))
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        member_count=len(members),
        members=member_responses
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    request: TeamUpdate,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to update team")
    
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if request.name:
        team.name = request.name
    if request.description is not None:
        team.description = request.description
    
    await db.commit()
    await db.refresh(team)
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        member_count=0,
        members=[]
    )


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.role == TeamRole.OWNER
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only owner can delete team")
    
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    await db.delete(team)
    await db.commit()
    
    return {"message": "Team deleted successfully"}


@router.post("/{team_id}/invitations", response_model=InvitationResponse)
async def create_invitation(
    team_id: int,
    request: InvitationCreate,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to invite members")
    
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    invitation = TeamInvitation(
        team_id=team_id,
        email=request.email,
        role=TeamRole(request.role),
        invited_by=user_id,
        expires_at=datetime.now() + timedelta(days=7)
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    
    return InvitationResponse(
        id=invitation.id,
        team_id=invitation.team_id,
        email=invitation.email,
        role=invitation.role.value if isinstance(invitation.role, TeamRole) else invitation.role,
        status=invitation.status.value if isinstance(invitation.status, InvitationStatus) else invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at
    )


@router.get("/{team_id}/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    team_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this team")
    
    inv_result = await db.execute(
        select(TeamInvitation).where(TeamInvitation.team_id == team_id)
    )
    invitations = inv_result.scalars().all()
    
    return [
        InvitationResponse(
            id=inv.id,
            team_id=inv.team_id,
            email=inv.email,
            role=inv.role.value if isinstance(inv.role, TeamRole) else inv.role,
            status=inv.status.value if isinstance(inv.status, InvitationStatus) else inv.status,
            created_at=inv.created_at,
            expires_at=inv.expires_at
        )
        for inv in invitations
    ]


@router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(select(TeamInvitation).where(TeamInvitation.id == invitation_id))
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invitation already processed")
    
    if invitation.expires_at < datetime.now():
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.email != invitation.email:
        raise HTTPException(status_code=403, detail="This invitation was sent to a different email")
    
    member = TeamMember(
        team_id=invitation.team_id,
        user_id=user_id,
        role=invitation.role
    )
    db.add(member)
    
    invitation.status = InvitationStatus.ACCEPTED
    await db.commit()
    
    return {"message": "Successfully joined the team"}


@router.delete("/{team_id}/members/{member_id}")
async def remove_member(
    team_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    current_member = result.scalar_one_or_none()
    
    target_result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    target_member = target_result.scalar_one_or_none()
    
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if not current_member:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    
    if current_member.role == TeamRole.OWNER:
        pass
    elif current_member.role == TeamRole.ADMIN:
        if target_member.role == TeamRole.OWNER or target_member.role == TeamRole.ADMIN:
            raise HTTPException(status_code=403, detail="Cannot remove admins or owners")
    elif user_id != target_member.user_id:
        raise HTTPException(status_code=403, detail="Cannot remove other members")
    
    await db.delete(target_member)
    await db.commit()
    
    return {"message": "Member removed successfully"}


@router.put("/{team_id}/members/{member_id}/role")
async def update_member_role(
    team_id: int,
    member_id: int,
    new_role: TeamRole,
    db: AsyncSession = Depends(get_db_dependency),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.role == TeamRole.OWNER
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only owner can change roles")
    
    target_result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    target_member = target_result.scalar_one_or_none()
    
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if target_member.role == TeamRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change owner's role")
    
    target_member.role = new_role
    await db.commit()
    
    return {"message": "Role updated successfully"}
