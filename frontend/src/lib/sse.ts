// Parse a Server-Sent-Events byte stream into successive JSON `data:` payloads.
//
// SSE frames are delimited by a blank line ("\n\n"). Network chunks do not line
// up with frames — one read can carry half a frame or several — so we buffer and
// only emit complete frames, keeping any trailing partial for the next read.
// Generic over T: the caller says what shape each `data:` JSON has.
export async function* parseSSEStream<T>(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<T> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? ""; // last item may be an incomplete frame

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      yield JSON.parse(line.slice(5).trim()) as T;
    }
  }
}
