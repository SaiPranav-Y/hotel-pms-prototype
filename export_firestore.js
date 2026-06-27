/**
 * Exports Firestore collections (reservations, temples) to local JSON files.
 * Uses the Firestore REST API with the project's web API key.
 * 
 * Run: node export_firestore.js
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

const PROJECT_ID = 'hotel-pms-prototype';
const API_KEY = 'AIzaSyC12tJyB-MuOt6wQLqMTElecRJ1j1BpYfM';

function fetchCollection(collectionId) {
  return new Promise((resolve, reject) => {
    const url = `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents/${collectionId}?key=${API_KEY}&pageSize=500`;

    https.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) {
            reject(new Error(`API Error: ${parsed.error.message}`));
            return;
          }
          const documents = (parsed.documents || []).map(doc => {
            const id = doc.name.split('/').pop();
            const fields = {};
            for (const [key, valueObj] of Object.entries(doc.fields || {})) {
              fields[key] = parseFirestoreValue(valueObj);
            }
            return { id, ...fields };
          });
          resolve(documents);
        } catch (e) {
          reject(e);
        }
      });
      res.on('error', reject);
    }).on('error', reject);
  });
}

function parseFirestoreValue(valueObj) {
  if (valueObj.stringValue !== undefined) return valueObj.stringValue;
  if (valueObj.integerValue !== undefined) return parseInt(valueObj.integerValue);
  if (valueObj.doubleValue !== undefined) return valueObj.doubleValue;
  if (valueObj.booleanValue !== undefined) return valueObj.booleanValue;
  if (valueObj.timestampValue !== undefined) return valueObj.timestampValue;
  if (valueObj.nullValue !== undefined) return null;
  if (valueObj.arrayValue) {
    return (valueObj.arrayValue.values || []).map(parseFirestoreValue);
  }
  if (valueObj.mapValue) {
    const map = {};
    for (const [k, v] of Object.entries(valueObj.mapValue.fields || {})) {
      map[k] = parseFirestoreValue(v);
    }
    return map;
  }
  return valueObj;
}

async function main() {
  const outputDir = path.join(__dirname, 'firestore_export');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir);
  }

  console.log('Fetching reservations...');
  try {
    const reservations = await fetchCollection('reservations');
    const resFile = path.join(outputDir, 'reservations.json');
    fs.writeFileSync(resFile, JSON.stringify(reservations, null, 2));
    console.log(`  Saved ${reservations.length} reservations to ${resFile}`);
  } catch (e) {
    console.error('  Failed to fetch reservations:', e.message);
  }

  console.log('Fetching temples...');
  try {
    const temples = await fetchCollection('temples');
    const temFile = path.join(outputDir, 'temples.json');
    fs.writeFileSync(temFile, JSON.stringify(temples, null, 2));
    console.log(`  Saved ${temples.length} temples to ${temFile}`);
  } catch (e) {
    console.error('  Failed to fetch temples:', e.message);
  }

  console.log('\nDone! Files saved in: firestore_export/');
}

main();
