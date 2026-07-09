from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.user import User
from app.models.blog import BlogPost
from app.schemas.blog import BlogCreate, BlogUpdate, BlogResponse

router = APIRouter()


@router.get("/blog")
@limiter.limit("120/minute")
def list_all_blog_posts(
    request: Request,
    current_user: User = Depends(require_permission("blog:manage")),
    db: Session = Depends(get_db),
):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return {"blog": [BlogResponse.model_validate(p).model_dump() for p in posts]}


@router.post("/blog", status_code=201)
@limiter.limit("30/minute")
def create_blog_post(
    request: Request,
    data: BlogCreate,
    current_user: User = Depends(require_permission("blog:manage")),
    db: Session = Depends(get_db),
):
    existing = db.query(BlogPost).filter(BlogPost.slug == data.slug).first()
    if existing:
        raise BadRequestException(detail="A post with this slug already exists")

    post_data = data.model_dump()
    if data.is_published:
        post_data["published_at"] = datetime.now(timezone.utc)
    post = BlogPost(**post_data)
    db.add(post)
    db.commit()
    db.refresh(post)
    return BlogResponse.model_validate(post).model_dump()


@router.patch("/blog/{post_id}")
@limiter.limit("30/minute")
def update_blog_post(
    request: Request,
    post_id: UUID,
    data: BlogUpdate,
    current_user: User = Depends(require_permission("blog:manage")),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise NotFoundException(detail="Blog post not found")

    update_data = data.model_dump(exclude_none=True)
    if "is_published" in update_data and update_data["is_published"] and not post.published_at:
        update_data["published_at"] = datetime.now(timezone.utc)
    for key, value in update_data.items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return BlogResponse.model_validate(post).model_dump()


@router.delete("/blog/{post_id}")
@limiter.limit("30/minute")
def delete_blog_post(
    request: Request,
    post_id: UUID,
    current_user: User = Depends(require_permission("blog:manage")),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise NotFoundException(detail="Blog post not found")
    db.delete(post)
    db.commit()
    return {"message": "Blog post deleted"}
