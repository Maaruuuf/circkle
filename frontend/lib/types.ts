export type Role = "user" | "admin";
export type ReactionType = "like" | "love" | "haha" | "wow" | "sad";

export interface Me {
  id: string;
  email: string;
  username: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  role: Role;
  is_email_verified: boolean;
  has_password: boolean;
  created_at: string;
}

export interface UserSummary {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  bio?: string | null;
}

export interface PublicProfile {
  id: string;
  username: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  created_at: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  is_following: boolean;
  is_me: boolean;
}

export interface Post {
  id: string;
  content: string | null;
  image_url: string | null;
  created_at: string;
  updated_at: string;
  author: UserSummary;
  reaction_count: number;
  comment_count: number;
  my_reaction: ReactionType | null;
}

export interface Comment {
  id: string;
  post_id: string;
  content: string;
  created_at: string;
  author: UserSummary;
}

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

export interface ReactionSummary {
  post_id: string;
  reaction_count: number;
  my_reaction: ReactionType | null;
  by_type: Record<string, number>;
}

export interface MediaUpload {
  id: string;
  url: string;
  width: number;
  height: number;
}

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  is_email_verified: boolean;
  deactivated_at: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface AdminStats {
  users: number;
  active_users: number;
  posts: number;
  comments: number;
  reactions: number;
}
