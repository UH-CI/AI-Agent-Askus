import { z } from "zod";

import { createTRPCRouter, publicProcedure } from "~/server/api/trpc";
import axios from "axios";

export const chatRouter = createTRPCRouter({
  response: publicProcedure
    .input(
      z.object({
        input: z.array(
          z.object({ type: z.enum(["human", "ai"]), content: z.string() }),
        ),
        retriever: z.enum(["default", "askus", "policies"]).default("default"),
      }),
    )
    .output(
      z.object({
        message: z.object({
          type: z.enum(["ai"]),
          content: z.string(),
        }),
        sources: z.array(z.string()),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const body = {
        input: {
          messages: input.input,
          retriever: input.retriever,
        },
      };

      const response = await axios.post(
        "http://localhost:8000/askus/invoke",
        body,
      );

      const sources = response.data.output.sources;
      const message = response.data.output.message;

      return {
        message: {
          type: message.type,
          content: message.content,
        },
        sources,
      };
    }),
});
