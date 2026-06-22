import { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";
import { SiweMessage } from "siwe";

export const authOptions: NextAuthOptions = {
  providers: [
    // 1. Google OAuth
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),

    // 2. SIWE (MetaMask / Ethereum)
    CredentialsProvider({
      id: "siwe",
      name: "MetaMask",
      credentials: {
        message: { label: "Message", type: "text" },
        signature: { label: "Signature", type: "text" },
      },
      async authorize(credentials) {
        try {
          if (!credentials?.message || !credentials?.signature) return null;

          const messageData = JSON.parse(credentials.message);
          const siwe = new SiweMessage(messageData);

          const result = await siwe.verify({ 
            signature: credentials.signature,
            domain: siwe.domain,
            nonce: siwe.nonce,
          });

          if (!result.success) {
            console.error("SIWE verification failed:", result.error);
            return null;
          }

          return {
            id: siwe.address,
            name: `${siwe.address.slice(0, 6)}...${siwe.address.slice(-4)}`,
            email: `${siwe.address}@eth.wallet`,
            image: null,
          };
        } catch (e) {
          console.error("SIWE auth failed:", e);
          return null;
        }
      },
    }),

    // 3. SIWS (Solana / Phantom)
    CredentialsProvider({
      id: "siws",
      name: "Phantom",
      credentials: {
        message: { label: "Message", type: "text" },
        signature: { label: "Signature", type: "text" },
        publicKey: { label: "Public Key", type: "text" },
      },
      async authorize(credentials) {
        try {
          if (!credentials?.message || !credentials?.signature || !credentials?.publicKey) return null;

          const message = credentials.message;
          const signature = credentials.signature;
          const publicKey = credentials.publicKey;

          return {
            id: publicKey,
            name: `${publicKey.slice(0, 4)}...${publicKey.slice(-4)}`,
            email: `${publicKey}@sol.wallet`,
            image: null,
          };
        } catch (e) {
          console.error("SIWS auth failed:", e);
          return null;
        }
      },
    }),

    // 4. SIWB (Base / Coinbase Wallet)
    CredentialsProvider({
      id: "siwb",
      name: "Coinbase",
      credentials: {
        message: { label: "Message", type: "text" },
        signature: { label: "Signature", type: "text" },
      },
      async authorize(credentials) {
        try {
          if (!credentials?.message || !credentials?.signature) return null;

          const messageData = JSON.parse(credentials.message);
          const siwe = new SiweMessage(messageData);

          const result = await siwe.verify({ 
            signature: credentials.signature,
            domain: siwe.domain,
            nonce: siwe.nonce,
          });

          if (!result.success) {
            console.error("SIWB verification failed:", result.error);
            return null;
          }

          return {
            id: siwe.address,
            name: `${siwe.address.slice(0, 6)}...${siwe.address.slice(-4)}`,
            email: `${siwe.address}@base.wallet`,
            image: null,
          };
        } catch (e) {
          console.error("SIWB auth failed:", e);
          return null;
        }
      },
    }),

    // 5. SIBSC (BNB Chain / MetaMask, Trust Wallet, etc.)
    CredentialsProvider({
      id: "sibsc",
      name: "BSC Wallet",
      credentials: {
        message: { label: "Message", type: "text" },
        signature: { label: "Signature", type: "text" },
      },
      async authorize(credentials) {
        try {
          if (!credentials?.message || !credentials?.signature) return null;

          const messageData = JSON.parse(credentials.message);
          const siwe = new SiweMessage(messageData);

          const result = await siwe.verify({ 
            signature: credentials.signature,
            domain: siwe.domain,
            nonce: siwe.nonce,
          });

          if (!result.success) {
            console.error("SIBSC verification failed:", result.error);
            return null;
          }

          return {
            id: siwe.address,
            name: `${siwe.address.slice(0, 6)}...${siwe.address.slice(-4)}`,
            email: `${siwe.address}@bsc.wallet`,
            image: null,
          };
        } catch (e) {
          console.error("SIBSC auth failed:", e);
          return null;
        }
      },
    }),
  ],

  pages: {
    signIn: "/sign-in",
    error: "/sign-in",
  },

  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60,
  },

  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id;
        token.provider = account?.provider;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
        (session.user as any).provider = token.provider;
      }
      return session;
    },
  },
};
