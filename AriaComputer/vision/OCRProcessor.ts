/**
 * Aria OCR Processor
 * Extracts text tokens and their exact on-screen bounding boxes.
 */

export interface OCRToken {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export class OCRProcessor {
  public parseScreenTokens(textTokens: OCRToken[] = []): OCRToken[] {
    return textTokens;
  }

  public findText(query: string, tokens: OCRToken[]): OCRToken | null {
    const clean = query.trim().toLowerCase();
    for (const t of tokens) {
      if (t.text.toLowerCase().includes(clean)) {
        return t;
      }
    }
    return null;
  }
}
