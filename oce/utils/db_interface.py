"""
Functions to interface to the database.
Supports both SQLite and PostgreSQL based on USE_POSTGRESQL environment variable.
"""

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeAlias
from uuid import uuid4 as create_uuid
from flask import current_app, g
from .. import password_hasher
from .models import Comment, Post, User
from datetime import datetime
import pytz

DatabaseRow: TypeAlias = dict[str, Any]

# Check which database to use
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

if USE_POSTGRESQL:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3 as sql


def _dict_factory(cursor, row: Sequence) -> DatabaseRow:
    """Factory for SQLite to return dict rows."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    """Retrieve the database connection from the app.

    Attempts to open a new connection if database has not been open yet.

    Returns:
        Connection to the database for querying.
    """
    db = getattr(g, '_database', None)
    
    if db is None:
        if USE_POSTGRESQL:
            # PostgreSQL connection
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError('DATABASE_URL environment variable not set')
            
            db = psycopg2.connect(
                database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            # SQLite connection
            if not isinstance(current_app.static_folder, str):
                raise FileNotFoundError(
                    'App static folder not registered properly. Unable to locate database.'
                )
            con = sql.connect(Path(current_app.static_folder) / current_app.config['DB_NAME'])
            con.row_factory = _dict_factory
            db = con
        
        g._database = db
    
    return db


def close_db(e=None):
    """Close the database connection."""
    db = g.pop('_database', None)
    if db is not None:
        db.close()


def _get_placeholder():
    """Get the correct SQL placeholder for the current database."""
    return '%s' if USE_POSTGRESQL else '?'


def _execute_query(cursor, query, params=None):
    """Execute a query with the correct placeholder syntax."""
    if USE_POSTGRESQL:
        # PostgreSQL uses %s
        pg_query = query.replace('?', '%s')
        cursor.execute(pg_query, params or ())
    else:
        # SQLite uses ?
        cursor.execute(query, params or ())


# Methods for Users


def create_user(
    username: str,
    email: str,
    password: str,
    profile_pic: bytes | None = None,
    about_me: str = '',
) -> None:
    """Creates a new user in the database.

    Args:
        username: User's user/display name.
        email: User's email.
        password: User's password. Will be hashed.
        profile_pic: User's profile picture as raw bytes. Defaults to None.
        about_me: User's about me description. Defaults to ''.
    """
    con = get_db()
    cur = con.cursor()

    if profile_pic is None:
        default_pic_path = Path(current_app.static_folder) / 'images' / '__DEFAULT.jpg'
        if default_pic_path.exists():
            with open(default_pic_path, 'rb') as fp:
                profile_pic = fp.read()
        else:
            profile_pic = b''

    eastern = pytz.timezone('US/Eastern')
    now_est = datetime.now(eastern)
    
    user_uuid = str(create_uuid())
    hashed_password = password_hasher.hash(password)
    
    new_user_data = (
        user_uuid,
        username,
        email,
        hashed_password,
        profile_pic,
        about_me,
        now_est if USE_POSTGRESQL else now_est.isoformat()
    )

    if USE_POSTGRESQL:
        cur.execute(
            'INSERT INTO users (user_uuid, username, email, password, profile_pic, about_me, datetime_created) VALUES (%s, %s, %s, %s, %s, %s, %s);',
            new_user_data
        )
    else:
        cur.execute(
            'INSERT INTO USERS VALUES(?, ?, ?, ?, ?, ?, ?);',
            new_user_data
        )
    con.commit()


def get_user_by_uuid(user_uuid: str) -> DatabaseRow | None:
    """Retrieve user data given a UUID.

    Args:
        user_uuid: UUID of user.

    Returns:
        Database query if the UUID exists, None otherwise.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE user_uuid = %s;', (user_uuid,))
        datum = cur.fetchone()
        return dict(datum) if datum else None
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE user_uuid = ?;', (user_uuid,)).fetchone()
        return datum


def get_user_by_email(email: str) -> DatabaseRow | None:
    """Retrieve user data given an email.

    Args:
        email: Email of user.

    Returns:
        Database query if the email exists, None otherwise.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE email = %s;', (email,))
        datum = cur.fetchone()
        return dict(datum) if datum else None
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE email = ?;', (email,)).fetchone()
        return datum


def get_user_by_username(username: str) -> DatabaseRow | None:
    """Retrieve user data given a username.

    Args:
        username: Username of user.

    Returns:
        Database query if the username exists, None otherwise.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE username = %s;', (username,))
        datum = cur.fetchone()
        return dict(datum) if datum else None
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE username = ?;', (username,)).fetchone()
        return datum


def update_user_username(user: User, username: str) -> None:
    """Update a user's username.

    Args:
        user: User to be edited.
        username: New username.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET username = {placeholder} WHERE user_uuid = {placeholder};',
        (username, user.user_uuid)
    )
    con.commit()


def update_user_email(user: User, email: str) -> None:
    """Update a user's email.

    Args:
        user: User to be edited.
        email: New email.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET email = {placeholder} WHERE user_uuid = {placeholder};',
        (email, user.user_uuid)
    )
    con.commit()


def update_user_password(user: User, password: str) -> None:
    """Update a user's password.

    Args:
        user: User to be edited.
        password: New password. Will be hashed.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET password = {placeholder} WHERE user_uuid = {placeholder};',
        (password_hasher.hash(password), user.user_uuid)
    )
    con.commit()


def update_user_profile_pic(user: User, profile_pic: bytes) -> None:
    """Update a user's profile picture.

    Args:
        user: User to be edited.
        profile_pic: New profile pic.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET profile_pic = {placeholder} WHERE user_uuid = {placeholder};',
        (profile_pic, user.user_uuid)
    )
    con.commit()


def update_user_about_me(user: User, about_me: str) -> None:
    """Update user's about me.

    Args:
        user: User to be edited.
        about_me: New about me.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET about_me = {placeholder} WHERE user_uuid = {placeholder};',
        (about_me, user.user_uuid)
    )
    con.commit()


def delete_user(user: User) -> None:
    """Delete a user.

    Arguments:
        user: User to delete.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'users' if USE_POSTGRESQL else 'USERS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'DELETE FROM {table_name} WHERE user_uuid = {placeholder};',
        (user.user_uuid,)
    )
    con.commit()


# Methods for Posts


def create_post(
    author: str,
    text_content: str,
) -> None:
    """Create a new post (temporary simplified version).

    Args:
        author: Author username.
        text_content: Content of the post.
    """
    con = get_db()
    cur = con.cursor()

    new_post_data = (
        str(create_uuid()),
        author,
        text_content,
        'None',
        'None',
        'None',
        'None',
        'None',
        'None',
        'None',
        None
    )

    if USE_POSTGRESQL:
        cur.execute(
            'INSERT INTO posts (post_uuid, author_uuid, text_content, tag1, tag2, tag3, tag4, tag5, location, datetime, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);',
            new_post_data
        )
    else:
        cur.execute(
            'INSERT INTO POSTS VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_post_data
        )
    con.commit()


def get_all_posts():
    """Retrieve all posts from the database."""
    con = get_db()
    cur = con.cursor()
    
    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT post_uuid, author_uuid, text_content FROM {table_name};')
        rows = cur.fetchall()
        posts = [dict(row) for row in rows]
    else:
        cur.execute(f'SELECT post_uuid, author_uuid, text_content FROM {table_name};')
        rows = cur.fetchall()
        posts = [
            {
                'post_uuid': row['post_uuid'],
                'author_uuid': row['author_uuid'],
                'text_content': row['text_content']
            }
            for row in rows
        ]
    return posts


def get_post_by_uuid(post_uuid: str) -> DatabaseRow | None:
    """Retrieve a post by UUID.

    Args:
        post_uuid: UUID of the post.

    Returns:
        Database query if the post exists, None otherwise.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE post_uuid = %s;', (post_uuid,))
        datum = cur.fetchone()
        return dict(datum) if datum else None
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE post_uuid = ?;', (post_uuid,)).fetchone()
        return datum


def get_posts_by_author(author: User) -> list[DatabaseRow]:
    """Retrieve all posts by a certain author.

    Args:
        author: Author of the posts.

    Returns:
        All posts by specified author.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE author_uuid = %s;', (author.user_uuid,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE author_uuid = ?;', (author.user_uuid,)).fetchall()
        return datum


def get_posts_by_tag(tag: str) -> list[DatabaseRow]:
    """Retrieve posts by tag.

    Args:
        tag: Tag of the posts.

    Raises:
        ValueError: Supplied tag was empty.

    Returns:
        All posts with specified tag.
    """
    if not tag:
        raise ValueError('Cannot query for posts based on empty tag.')

    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(
            f'SELECT * FROM {table_name} WHERE tag1 = %s OR tag2 = %s OR tag3 = %s OR tag4 = %s OR tag5 = %s;',
            (tag, tag, tag, tag, tag)
        )
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(
            f'SELECT * FROM {table_name} WHERE tag1 = ? OR tag2 = ? OR tag3 = ? OR tag4 = ? OR tag5 = ?;',
            (tag, tag, tag, tag, tag)
        ).fetchall()
        return datum


def get_posts_by_datetime(datetime_str: str) -> list[DatabaseRow]:
    """Retrieve posts by date- and timestamp.

    Args:
        datetime_str: Date- and timestamp of the posts.

    Returns:
        All posts with specified date- and timestamp.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE datetime = %s;', (datetime_str,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE datetime = ?;', (datetime_str,)).fetchall()
        return datum


def get_posts_by_location(location: str) -> list[DatabaseRow]:
    """Retrieve posts by location.

    Args:
        location: Location of the posts.

    Returns:
        All posts with specified location.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE location = %s;', (location,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE location = ?;', (location,)).fetchall()
        return datum


def update_post_text_content(post: Post, text_content: str) -> None:
    """Update a post's content.

    Args:
        post: Post to be edited.
        text_content: New content for the post.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET text_content = {placeholder} WHERE post_uuid = {placeholder};',
        (text_content, post.post_uuid)
    )
    con.commit()


def update_post_tags(post: Post, tags: tuple[str, str, str, str, str]) -> None:
    """Update a post's tags.

    Args:
        post: Post to be edited.
        tags: New tags for the post.
    """
    con = get_db()
    cur = con.cursor()

    tag1, tag2, tag3, tag4, tag5 = tags
    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'

    if USE_POSTGRESQL:
        cur.execute(
            f'UPDATE {table_name} SET tag1 = {placeholder}, tag2 = {placeholder}, tag3 = {placeholder}, tag4 = {placeholder}, tag5 = {placeholder} WHERE post_uuid = {placeholder};',
            (tag1, tag2, tag3, tag4, tag5, post.post_uuid)
        )
    else:
        cur.execute(f'UPDATE {table_name} SET tag1 = ? WHERE post_uuid = ?;', (tag1, post.post_uuid))
        cur.execute(f'UPDATE {table_name} SET tag2 = ? WHERE post_uuid = ?;', (tag2, post.post_uuid))
        cur.execute(f'UPDATE {table_name} SET tag3 = ? WHERE post_uuid = ?;', (tag3, post.post_uuid))
        cur.execute(f'UPDATE {table_name} SET tag4 = ? WHERE post_uuid = ?;', (tag4, post.post_uuid))
        cur.execute(f'UPDATE {table_name} SET tag5 = ? WHERE post_uuid = ?;', (tag5, post.post_uuid))
    con.commit()


def update_post_image(post: Post, image: bytes) -> None:
    """Update a post's image.

    Args:
        post: Post to be edited.
        image: New image for the post.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET image = {placeholder} WHERE post_uuid = {placeholder};',
        (image, post.post_uuid)
    )
    con.commit()


def update_post_datetime(post: Post, datetime_str: str) -> None:
    """Update a post's date- and timestamp.

    Args:
        post: Post to be edited.
        datetime_str: New date- and timestamp for the post.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET datetime = {placeholder} WHERE post_uuid = {placeholder};',
        (datetime_str, post.post_uuid)
    )
    con.commit()


def update_post_location(post: Post, location: str) -> None:
    """Update a post's location.

    Args:
        post: Post to be edited.
        location: New location for the post.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET location = {placeholder} WHERE post_uuid = {placeholder};',
        (location, post.post_uuid)
    )
    con.commit()


def delete_post(post: Post) -> None:
    """Delete a post.

    Args:
        post: Post to delete.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'posts' if USE_POSTGRESQL else 'POSTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'DELETE FROM {table_name} WHERE post_uuid = {placeholder};',
        (post.post_uuid,)
    )
    con.commit()


# Methods for Comments


def create_comment(
    parent_post: Post,
    author: User,
    text_content: str,
    datetime_str: str,
) -> None:
    """Create a new comment for a post with content.

    Args:
        parent_post: Post the comment will be under.
        author: Author of the comment.
        text_content: Content of the comment.
        datetime_str: Date- and timestamp of the comment.
    """
    con = get_db()
    cur = con.cursor()

    new_comment_data = (
        str(create_uuid()),
        parent_post.post_uuid,
        author.user_uuid,
        text_content,
        datetime_str,
    )

    if USE_POSTGRESQL:
        cur.execute(
            'INSERT INTO comments (comment_uuid, parent_post_uuid, author_uuid, text_content, datetime) VALUES (%s, %s, %s, %s, %s);',
            new_comment_data
        )
    else:
        cur.execute(
            'INSERT INTO COMMENTS VALUES(?, ?, ?, ?, ?);',
            new_comment_data
        )
    con.commit()


def get_comment_by_uuid(comment_uuid: str) -> DatabaseRow | None:
    """Retrieve a comment by UUID.

    Args:
        comment_uuid: UUID of the comment.

    Returns:
        Database query if the comment exists, None otherwise.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE comment_uuid = %s;', (comment_uuid,))
        datum = cur.fetchone()
        return dict(datum) if datum else None
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE comment_uuid = ?;', (comment_uuid,)).fetchone()
        return datum


def get_comments_by_parent_post(parent_post: Post) -> list[DatabaseRow]:
    """Retrieve all comments under a certain post.

    Args:
        parent_post: Parent post of the comments.

    Returns:
        All comments under specified parent post.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE parent_post_uuid = %s;', (parent_post.post_uuid,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE parent_post_uuid = ?;', (parent_post.post_uuid,)).fetchall()
        return datum


def get_comments_by_author(author: User) -> list[DatabaseRow]:
    """Retrieve all comments by a certain author.

    Args:
        author: Author of the comments.

    Returns:
        All comments by specified author.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE author_uuid = %s;', (author.user_uuid,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE author_uuid = ?;', (author.user_uuid,)).fetchall()
        return datum


def get_comments_by_datetime(datetime_str: str) -> list[DatabaseRow]:
    """Retrieve comments by date- and timestamp.

    Args:
        datetime_str: Date- and timestamp of the comments.

    Returns:
        All comments with specified date- and timestamp.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    
    if USE_POSTGRESQL:
        cur.execute(f'SELECT * FROM {table_name} WHERE datetime = %s;', (datetime_str,))
        data = cur.fetchall()
        return [dict(row) for row in data]
    else:
        datum = cur.execute(f'SELECT * FROM {table_name} WHERE datetime = ?;', (datetime_str,)).fetchall()
        return datum


def update_comment_text_content(comment: Comment, text_content: str) -> None:
    """Update a comment's content.

    Args:
        comment: Comment to be edited.
        text_content: New content for the comment.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET text_content = {placeholder} WHERE comment_uuid = {placeholder};',
        (text_content, comment.comment_uuid)
    )
    con.commit()


def update_comment_datetime(comment: Comment, datetime_str: str) -> None:
    """Update a comment's date- and timestamp.

    Args:
        comment: Comment to be edited.
        datetime_str: New date- and timestamp for the comment.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'UPDATE {table_name} SET datetime = {placeholder} WHERE comment_uuid = {placeholder};',
        (datetime_str, comment.comment_uuid)
    )
    con.commit()


def delete_comment(comment: Comment) -> None:
    """Delete a comment.

    Args:
        comment: Comment to delete.
    """
    con = get_db()
    cur = con.cursor()

    table_name = 'comments' if USE_POSTGRESQL else 'COMMENTS'
    placeholder = '%s' if USE_POSTGRESQL else '?'
    
    cur.execute(
        f'DELETE FROM {table_name} WHERE comment_uuid = {placeholder};',
        (comment.comment_uuid,)
    )
    con.commit()