import { create } from "zustand";

type User = { id: number; email: string };

type State = {
  user: User | null;
  setUser: (u: User | null) => void;
};

export const useAuth = create<State>((set) => ({
  user: null,
  setUser: (u) => set({ user: u }),
}));