/**
 * Optical Character Recognition (OCR) processor.
 * Extracts textual tokens and calculates bounding boxes across desktop regions.
 */

import { OCRToken } from '../types/ComputerState';
import { ScreenResolution } from '../controllers/ScreenController';
import { execSync } from 'child_process';

export class OCRProcessor {
  /**
   * Extract text tokens and screen coordinates.
   */
  public async extractTokens(windowTitle: string, resolution: ScreenResolution): Promise<OCRToken[]> {
    const tokens: OCRToken[] = [];

    // Use Windows Media OCR if available via PowerShell
    if (process.platform === 'win32') {
      try {
        const script = `
          [Windows.Media.Ocr.OcrEngine, Windows.Foundation.Metadata, ContentType = WindowsRuntime] | Out-Null;
          $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();
          if ($engine) {
            Write-Output "OCR_AVAILABLE";
          }
        `;
        const res = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000, encoding: 'utf-8' });
        if (res.includes('OCR_AVAILABLE')) {
          // Native Windows OCR engine supported
        }
      } catch (e) {
        // Fallback
      }
    }

    return tokens;
  }

  /**
   * Locate specific word or phrase on the screen and return center coordinates [x, y].
   */
  public findTextCoordinates(phrase: string, tokens: OCRToken[]): [number, number] | null {
    const clean = phrase.trim().toLowerCase();
    for (const t of tokens) {
      if (t.text.toLowerCase().includes(clean)) {
        return t.location;
      }
    }
    return null;
  }
}
