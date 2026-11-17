# Exact competition-family classification

The unchanged review oracle flags 348 r18 placements and 300 broad-candidate placements. The candidate residue is exactly 60 company-heading collisions and 240 sole-domain-company matches. The final source holds all 60 collisions. The 240 remaining raw flags are justified below, one row per case, without changing the original oracle or its allowed-rule map.

For every `sole match` row: the supplied signer is Pat Smith / pat@harborlight.fleet.test, with **no explicit company**. The original blank has no Harbor company heading and no Pat name; `RECIPIENT:` has no role definition, `COMPANY` names no legal entity, and `none` has no heading. The affiliate shown in that row is the only Harbor-named company in the PDF. The input therefore does not identify Analytics (or any other legal entity) as Pat’s company. The placement follows the requested company-only exception; claiming a different known legal entity would require information absent from the input. Chris Jones / Witness / Schedule captions do not supply Pat’s company. The separate 24 controls confirm that explicitly supplying Analytics as Pat’s company makes the Group-only layouts hold.

For every `held collision` row, the candidate put Pat on a different named company while the original row included Analytics. The final result is `needs_sender` with no fields. Every such case also passed the real worker comparison.

IDs follow the exact 480-case generator order (zero based). The table includes all 300 candidate raw flags. Full inputs, original oracle, output fields and adjudication for all 480 cases are in [competition-classification.json](competition-classification.json).

| ID | Original heading | Extra line | Affiliate | Affiliate column | Long Fleet | Signers | Final classification | Pat signature/date y |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 82 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | none | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 86 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | none | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 90 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | none | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 94 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | none | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 98 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 102 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 106 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 110 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 114 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 118 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 122 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 126 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 130 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 134 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 138 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 142 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 146 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Witness: | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 150 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Witness: | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 154 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Witness: | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 158 | HARBOR LIGHT ANALYTICS INTERNATIONAL, INC. | Witness: | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 160 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 161 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 162 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 163 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 164 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 165 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 166 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 167 | RECIPIENT: | none | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 168 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 169 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 170 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 171 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 172 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 173 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 174 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 175 | RECIPIENT: | none | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 176 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 177 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 178 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 179 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 180 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 181 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 182 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 183 | RECIPIENT: | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 184 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 185 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 186 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 187 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 188 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 189 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 190 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 191 | RECIPIENT: | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 192 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 193 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 194 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 195 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 196 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 197 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 198 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 199 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 200 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 201 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 202 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 203 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 204 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 205 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 206 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 207 | RECIPIENT: | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 208 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 209 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 210 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 211 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 212 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 213 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 214 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 215 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 216 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 217 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 218 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 219 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 220 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 221 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 222 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 223 | RECIPIENT: | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 224 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 225 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 226 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 227 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 228 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 229 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 230 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 231 | RECIPIENT: | Witness: | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 232 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 233 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 234 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 235 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 236 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 237 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 238 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 239 | RECIPIENT: | Witness: | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 240 | COMPANY | none | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 241 | COMPANY | none | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 242 | COMPANY | none | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 243 | COMPANY | none | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 244 | COMPANY | none | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 245 | COMPANY | none | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 246 | COMPANY | none | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 247 | COMPANY | none | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 248 | COMPANY | none | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 249 | COMPANY | none | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 250 | COMPANY | none | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 251 | COMPANY | none | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 252 | COMPANY | none | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 253 | COMPANY | none | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 254 | COMPANY | none | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 255 | COMPANY | none | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 256 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 257 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 258 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 259 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 260 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 261 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 262 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 263 | COMPANY | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 264 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 265 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 266 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 267 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 268 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 269 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 270 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 271 | COMPANY | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 272 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 273 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 274 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 275 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 276 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 277 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 278 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 279 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 280 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 281 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 282 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 283 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 284 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 285 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 286 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 287 | COMPANY | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 288 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 289 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 290 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 291 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 292 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 293 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 294 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 295 | COMPANY | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 296 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 297 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 298 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 299 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 300 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 301 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 302 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 303 | COMPANY | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 304 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 305 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 306 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 307 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 308 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 309 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 310 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 311 | COMPANY | Witness: | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 312 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 313 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 314 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 315 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 316 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 317 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 318 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 319 | COMPANY | Witness: | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 320 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT GROUP, INC. | left | False | PAT | held collision | none |
| 322 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 324 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT GROUP, INC. | right | False | PAT | held collision | none |
| 326 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 328 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT VENTURES LLC | left | False | PAT | held collision | none |
| 330 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 332 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT VENTURES LLC | right | False | PAT | held collision | none |
| 334 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | none | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 336 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | held collision | none |
| 338 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 340 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | held collision | none |
| 342 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 344 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | held collision | none |
| 346 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 348 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | held collision | none |
| 350 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 352 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | PAT | held collision | none |
| 354 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 356 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | PAT | held collision | none |
| 358 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 360 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | PAT | held collision | none |
| 362 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 364 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | PAT | held collision | none |
| 366 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 368 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | held collision | none |
| 370 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 372 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | held collision | none |
| 374 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 376 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | held collision | none |
| 378 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 380 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | held collision | none |
| 382 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 384 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT GROUP, INC. | left | False | PAT | held collision | none |
| 386 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT GROUP, INC. | left | True | PAT | held collision | none |
| 388 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT GROUP, INC. | right | False | PAT | held collision | none |
| 390 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT GROUP, INC. | right | True | PAT | held collision | none |
| 392 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT VENTURES LLC | left | False | PAT | held collision | none |
| 394 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT VENTURES LLC | left | True | PAT | held collision | none |
| 396 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT VENTURES LLC | right | False | PAT | held collision | none |
| 398 | FLEET TEST CO. / HARBOR LIGHT ANALYTICS, INC. | Witness: | HARBOR LIGHT VENTURES LLC | right | True | PAT | held collision | none |
| 400 | none | none | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 401 | none | none | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 402 | none | none | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 403 | none | none | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 404 | none | none | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 405 | none | none | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 406 | none | none | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 407 | none | none | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 408 | none | none | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 409 | none | none | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 410 | none | none | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 411 | none | none | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 412 | none | none | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 413 | none | none | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 414 | none | none | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 415 | none | none | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 416 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 417 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 418 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 419 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 420 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 421 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 422 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 423 | none | Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 424 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 425 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 426 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 427 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 428 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 429 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 430 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 431 | none | Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 432 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 433 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 434 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 435 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 436 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 437 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 438 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 439 | none | See Schedule A attached hereto | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 440 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 441 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 442 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 443 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 444 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 445 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 446 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 447 | none | See Schedule A attached hereto | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 448 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 449 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 450 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 451 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 452 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 453 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 454 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 455 | none | Name: Chris Jones | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 456 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 457 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 458 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 459 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 460 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 461 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 462 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 463 | none | Name: Chris Jones | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
| 464 | none | Witness: | HARBOR LIGHT GROUP, INC. | left | False | PAT | sole match | 450 / 510 |
| 465 | none | Witness: | HARBOR LIGHT GROUP, INC. | left | False | DAN+PAT | sole match | 450 / 510 |
| 466 | none | Witness: | HARBOR LIGHT GROUP, INC. | left | True | PAT | sole match | 450 / 510 |
| 467 | none | Witness: | HARBOR LIGHT GROUP, INC. | left | True | DAN+PAT | sole match | 450 / 510 |
| 468 | none | Witness: | HARBOR LIGHT GROUP, INC. | right | False | PAT | sole match | 450 / 510 |
| 469 | none | Witness: | HARBOR LIGHT GROUP, INC. | right | False | DAN+PAT | sole match | 450 / 510 |
| 470 | none | Witness: | HARBOR LIGHT GROUP, INC. | right | True | PAT | sole match | 450 / 510 |
| 471 | none | Witness: | HARBOR LIGHT GROUP, INC. | right | True | DAN+PAT | sole match | 450 / 510 |
| 472 | none | Witness: | HARBOR LIGHT VENTURES LLC | left | False | PAT | sole match | 450 / 510 |
| 473 | none | Witness: | HARBOR LIGHT VENTURES LLC | left | False | DAN+PAT | sole match | 450 / 510 |
| 474 | none | Witness: | HARBOR LIGHT VENTURES LLC | left | True | PAT | sole match | 450 / 510 |
| 475 | none | Witness: | HARBOR LIGHT VENTURES LLC | left | True | DAN+PAT | sole match | 450 / 510 |
| 476 | none | Witness: | HARBOR LIGHT VENTURES LLC | right | False | PAT | sole match | 450 / 510 |
| 477 | none | Witness: | HARBOR LIGHT VENTURES LLC | right | False | DAN+PAT | sole match | 450 / 510 |
| 478 | none | Witness: | HARBOR LIGHT VENTURES LLC | right | True | PAT | sole match | 450 / 510 |
| 479 | none | Witness: | HARBOR LIGHT VENTURES LLC | right | True | DAN+PAT | sole match | 450 / 510 |
