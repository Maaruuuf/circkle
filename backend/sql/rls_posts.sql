-- OPTIONAL defence in depth: PostgreSQL Row Level Security (RLS) for posts.
-- NOT applied by any migration. See docs/SECURITY.md ("Row Level Security") before using.
--
-- Idea: even if application code forgets an ownership check, the database itself
-- refuses to let user A change or delete user B's posts.
--
-- Requirements for this to be meaningful:
--   1. The app connects as a role that does NOT own the tables and is not a superuser
--      (superusers and table owners bypass RLS unless FORCE is set).
--   2. Every request/transaction sets the acting user:
--        SELECT set_config('app.current_user_id', '<uuid>', true);   -- true = this transaction only
--        SELECT set_config('app.is_admin', 'false', true);
--   3. Background jobs / cascades must run as a separate privileged role.

ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Everyone may read posts.
CREATE POLICY posts_select_all ON posts
    FOR SELECT USING (true);

-- You may only insert posts as yourself.
CREATE POLICY posts_insert_own ON posts
    FOR INSERT WITH CHECK (author_id = current_setting('app.current_user_id', true)::uuid);

-- You may only change your own posts.
CREATE POLICY posts_update_own ON posts
    FOR UPDATE USING (author_id = current_setting('app.current_user_id', true)::uuid);

-- You may delete your own posts; admins may delete any.
CREATE POLICY posts_delete_own_or_admin ON posts
    FOR DELETE USING (
        author_id = current_setting('app.current_user_id', true)::uuid
        OR current_setting('app.is_admin', true) = 'true'
    );

-- Rollback:
--   DROP POLICY posts_select_all, posts_insert_own, posts_update_own, posts_delete_own_or_admin ON posts;
--   ALTER TABLE posts DISABLE ROW LEVEL SECURITY;
