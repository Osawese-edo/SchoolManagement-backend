from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.exceptions import NotFoundException
from app.models.blog import BlogPost

router = APIRouter()


@router.get("/blog")
@limiter.limit("60/minute")
def list_published_blog_posts(request: Request, db: Session = Depends(get_db)):
    posts = (
        db.query(BlogPost)
        .filter(BlogPost.is_published == True)
        .order_by(desc(BlogPost.published_at))
        .all()
    )
    return {"blog": [
        {
            "id": str(p.id),
            "title": p.title,
            "slug": p.slug,
            "excerpt": p.excerpt,
            "author": p.author,
            "featured_image_url": p.featured_image_url,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]}


@router.get("/blog/{slug}")
@limiter.limit("60/minute")
def get_blog_post(request: Request, slug: str, db: Session = Depends(get_db)):
    post = (
        db.query(BlogPost)
        .filter(BlogPost.slug == slug, BlogPost.is_published == True)
        .first()
    )
    if not post:
        raise NotFoundException(detail="Blog post not found")
    return {
        "id": str(post.id),
        "title": post.title,
        "slug": post.slug,
        "content": post.content,
        "excerpt": post.excerpt,
        "author": post.author,
        "featured_image_url": post.featured_image_url,
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }
