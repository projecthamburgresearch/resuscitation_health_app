/**
 * Sample TypeScript module for Blueprint testing.
 *
 * Expected entities:
 * - 1 FILE entity
 * - 2+ FUNCTION entities: greet, calculateTotal (arrow)
 * - 1 CLASS entity: UserService
 * - 2+ METHOD entities: UserService.getUser, UserService.createUser
 * - 1 INTERFACE entity: User
 * - 1 ENUM entity: Role
 * - 1+ IMPORT entities
 */

import { Request, Response } from 'express';

// Types
interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
}

enum Role {
  Admin = 'admin',
  User = 'user',
  Guest = 'guest',
}

type UserCreateInput = Omit<User, 'id'>;

// Constants
const MAX_PAGE_SIZE = 100;

// Regular function
function greet(name: string): string {
  return `Hello, ${name}!`;
}

// Arrow function
const calculateTotal = (items: number[], taxRate: number = 0.1): number => {
  if (items.length === 0) {
    return 0;
  }

  let total = 0;
  for (const item of items) {
    if (item > 0) {
      total += item;
    }
  }

  const message = greet('customer');
  return total * (1 + taxRate);
};

// Class with methods
class UserService {
  private users: User[] = [];

  async getUser(id: number): Promise<User | undefined> {
    if (id <= 0) {
      throw new Error('Invalid ID');
    }
    return this.users.find(u => u.id === id);
  }

  async createUser(input: UserCreateInput): Promise<User> {
    const newUser: User = {
      id: this.users.length + 1,
      ...input,
    };
    this.users.push(newUser);
    return newUser;
  }

  listUsers(page: number = 1, pageSize: number = 20): User[] {
    const start = (page - 1) * pageSize;
    return this.users.slice(start, start + pageSize);
  }
}

export { UserService, greet, calculateTotal };
export type { User, UserCreateInput };
