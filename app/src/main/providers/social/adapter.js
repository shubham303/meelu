import { ProviderAdapter } from "../registry.js";

export const SOCIAL_CAPABILITIES = [
  "accounts.create",
  "profiles.list",
  "profiles.connect",
  "profiles.disconnect",
  "posts.create",
  "posts.create_with_files",
  "posts.update",
  "posts.get",
  "posts.delete",
];

export class SocialAdapter extends ProviderAdapter {
  static get platforms() {
    return [];
  }

  async createAccount() {
    throw this.unsupported("accounts.create");
  }

  async connectLink() {
    throw this.unsupported("profiles.connect");
  }

  async listProfiles() {
    throw this.unsupported("profiles.list");
  }

  async disconnectProfile() {
    throw this.unsupported("profiles.disconnect");
  }

  async createPost() {
    throw this.unsupported("posts.create");
  }

  async createPostWithFiles() {
    throw this.unsupported("posts.create_with_files");
  }

  async updatePost() {
    throw this.unsupported("posts.update");
  }

  async getPost() {
    throw this.unsupported("posts.get");
  }

  async deletePost() {
    throw this.unsupported("posts.delete");
  }
}
