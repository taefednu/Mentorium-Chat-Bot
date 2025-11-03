import { PrismaClient } from '@prisma/client';

export const prisma = new PrismaClient();

export async function withPrisma<T>(callback: (client: PrismaClient) => Promise<T>): Promise<T> {
  try {
    return await callback(prisma);
  } finally {
    await prisma.$disconnect();
  }
}
