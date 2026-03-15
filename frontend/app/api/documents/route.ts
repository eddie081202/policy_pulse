import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const fileParam = searchParams.get('file');

  // Navigate from frontend directory up to the main project root, then to data
  const basePath = path.join(process.cwd(), '..', 'data', 'insurance_contracts');

  if (fileParam) {
    // Block local file inclusion vulnerabilities
    const safePath = path.normalize(fileParam).replace(/^(\.\.(\/|\\|$))+/, '');
    const filePath = path.join(basePath, safePath);
    
    if (fs.existsSync(filePath)) {
      const fileBuffer = fs.readFileSync(filePath);
      const ext = path.extname(filePath).toLowerCase();
      const contentType = ext === '.csv' ? 'text/csv' : 'application/pdf';
      return new NextResponse(fileBuffer, {
        headers: {
          'Content-Type': contentType,
          'Content-Disposition': `inline; filename="${path.basename(filePath)}"`,
        },
      });
    }
    return new NextResponse('File not found at ' + filePath, { status: 404 });
  }

  const results: any = {
    Health: [],
    Auto: [],
    Homeowners: [],
    'Life & Other': [],
    CSV: []
  };

  const traverse = (dir: string, category: string) => {
    const fullDir = path.join(basePath, dir);
    if (!fs.existsSync(fullDir)) return;
    
    const files = fs.readdirSync(fullDir);
    for (const f of files) {
      const stat = fs.statSync(path.join(fullDir, f));
      if (stat.isFile() && !f.startsWith('.')) {
        const ext = path.extname(f).replace('.', '');
        results[category].push({
          name: f,
          path: `${dir}/${f}`,
          type: ext,
          size: (stat.size / (1024 * 1024)).toFixed(2) + ' MB'
        });
      }
    }
  }

  traverse('health', 'Health');
  traverse('auto', 'Auto');
  traverse('homeowners', 'Homeowners');
  traverse('life_other', 'Life & Other');
  traverse('csv', 'CSV');

  return NextResponse.json(results);
}
