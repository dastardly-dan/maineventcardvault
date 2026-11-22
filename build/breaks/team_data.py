# Team-break data. Format per product: {"base": {team: "a;b"}, "other": {team: "a;b"}}
# "other" = autographs and inserts (names not always in the base set). Source: checklistcenter.com.

def T(s):
    out = {}
    for line in s.strip().splitlines():
        team, names = line.split(':', 1)
        out[team.strip()] = [n.strip() for n in names.split(';') if n.strip()]
    return out

NFL_CHROME = dict(base=T('''
Cardinals: Jacoby Brissett;James Conner;Trey Benson;Marvin Harrison Jr.;Michael Wilson;Trey McBride;Denzel Burke;Will Johnson;Budda Baker;Carson Beck;Jeremiyah Love;Reggie Virgil
Falcons: Michael Penix Jr.;Tua Tagovailoa;Bijan Robinson;Brian Robinson Jr.;Drake London;Olamide Zaccheaus;Kyle Pitts Sr.;Chris Lindstrom;Jalon Walker;Zachariah Branch;Avieon Terrell;Harold Perkins Jr.
Ravens: Lamar Jackson;Derrick Henry;Rashod Bateman;Devontez Walker;Zay Flowers;Mark Andrews;Trey Hendrickson;Roquan Smith;Nate Wiggins;Kyle Hamilton;Ja'Kobi Lane;Elijah Sarratt;Zion Young
Bills: Josh Allen;James Cook;DJ Moore;Keon Coleman;Khalil Shakir;Dawson Knox;Dalton Kincaid;Dion Dawkins;Christian Benford;Skyler Bell;T.J. Parker;Davison Igbinosun
Panthers: Bryce Young;Chuba Hubbard;Trevor Etienne;Tetairoa McMillan;Xavier Legette;Jimmy Horn Jr.;Tommy Tremble;Derrick Brown;Jaycee Horn;Chris Brazzell II;Lee Hunter;Will Lee III
Bears: Caleb Williams;D'Andre Swift;Kyle Monangai;Rome Odunze;Luther Burden III;Colston Loveland;Joe Thuney;Darnell Wright;Montez Sweat;Jaylon Johnson;Zavion Thomas;Sam Roush;Dillon Thieneman
Bengals: Joe Burrow;Chase Brown;Ja'Marr Chase;Tee Higgins;Andrei Iosivas;Jonathan Allen;Dexter Lawrence II;Evan McPherson;Colbie Young;Cashius Howell;Tacario Davis
Browns: Shedeur Sanders;Quinshon Judkins;Dylan Sampson;Jerry Jeudy;Harold Fannin Jr.;Mason Graham;Carson Schwesinger;Denzel Ward;Grant Delpit;Taylen Green;KC Concepcion;Denzel Boston;Emmanuel McNeil-Warren
Rams: Myles Garrett;Matthew Stafford;Kyren Williams;Blake Corum;Davante Adams;Puka Nacua;Jordan Whittington;Terrance Ferguson;Byron Young;Trent McDuffie;Ty Simpson;CJ Daniels;Max Klare
Cowboys: Dak Prescott;Javonte Williams;George Pickens;CeeDee Lamb;Jake Ferguson;Quinnen Williams;Kenny Clark;DeMarvion Overshown;DaRon Bland;Brandon Aubrey;Malachi Lawrence;Jaishawn Barham;Caleb Downs
Broncos: Bo Nix;J.K. Dobbins;RJ Harvey;Courtland Sutton;Jaylen Waddle;Marvin Mims Jr.;Zach Allen;Nik Bonitto;Talanoa Hufanga;Pat Surtain II;Jonah Coleman;Justin Joly;Dallen Bentley
Lions: Jared Goff;Jahmyr Gibbs;Isiah Pacheco;Isaac TeSlaa;Jameson Williams;Amon-Ra St. Brown;Sam LaPorta;Aidan Hutchinson;Jack Campbell;Brian Branch;Kendrick Law;Derrick Moore;Keith Abney II
Packers: Jordan Love;Josh Jacobs;Christian Watson;Matthew Golden;Jayden Reed;Savion Williams;Tucker Kraft;Edgerrin Cooper;Micah Parsons;Xavier McKinney;Chris McClellan;Dani Dennis-Sutton;Brandon Cisse
Texans: CJ Stroud;David Montgomery;Woody Marks;Nico Collins;Jayden Higgins;Dalton Schultz;Will Anderson Jr.;Derek Stingley Jr.;Kamari Lassiter;Reed Blankenship;Marlin Klein;Keylan Rutledge;Kayden McDonald
Colts: Daniel Jones;Riley Leonard;Jonathan Taylor;Alec Pierce;Josh Downs;Tyler Warren;Quenton Nelson;DeForest Buckner;Laiatu Latu;Sauce Gardner;Deion Burks;CJ Allen;A.J. Haulcy
Jaguars: Trevor Lawrence;Bhayshul Tuten;Brian Thomas Jr.;Jakobi Meyers;Travis Hunter;Brenton Strange;Travon Walker;Josh Hines-Allen;Cam Little;Josh Cameron;Nate Boerkircher;Albert Regis
Chiefs: Patrick Mahomes II;Kenneth Walker III;Xavier Worthy;Rashee Rice;Tyquan Thornton;Travis Kelce;Creed Humphrey;Chris Jones;George Karlaftis;Nick Bolton;Garrett Nussmeier;Emmett Johnson;Peter Woods;Mansoor Delane
Raiders: Kirk Cousins;Ashton Jeanty;Jack Bech;Tre Tucker;Dont'e Thornton Jr.;Brock Bowers;Maxx Crosby;Quay Walker;Nakobe Dean;Jeremy Chinn;Fernando Mendoza;Mike Washington Jr.;Jermod McCoy
Chargers: Justin Herbert;Omarion Hampton;Quentin Johnston;Tre Harris III;Ladd McConkey;Oronde Gadsden;Joe Alt;Khalil Mack;Derwin James;Cameron Dicker;Brenen Thompson;Akheem Mesidor;Genesis Smith
Dolphins: Malik Willis;Quinn Ewers;De'Von Achane;Jaylen Wright;Malik Washington;Ollie Gordon II;Kenneth Grant;Chop Robinson;Caleb Douglas;Jacob Rodriguez;Chris Bell
Vikings: Kyler Murray;J.J. McCarthy;Aaron Jones Sr.;Justin Jefferson;Jordan Addison;Jauan Jennings;T.J. Hockenson;Dallas Turner;Byron Murphy Jr.;Demond Claiborne;Caleb Banks;Jake Golday
Patriots: Drake Maye;Rhamondre Stevenson;TreVeyon Henderson;Kayshon Boutte;Kyle Williams;Mack Hollins;Hunter Henry;Robert Spillane;Christian Gonzalez;Behren Morton;Eli Raridon;Caleb Lomu
Saints: Tyler Shough;Spencer Rattler;Travis Etienne Jr.;Alvin Kamara;Chris Olave;Juwan Johnson;Taysom Hill;Bryan Bresee;Kool-Aid McKinstry;Jordyn Tyson;Bryce Lance;Christen Miller
Giants: Jaxson Dart;Cam Skattebo;Tyrone Tracy Jr.;Malik Nabers;Darius Slayton;Isaiah Likely;Theo Johnson;Brian Burns;Abdul Carter;Malachi Fields;Francis Mauigoa;Arvell Reese;Colton Hood
Jets: Geno Smith;Breece Hall;Braelon Allen;Adonai Mitchell;Garrett Wilson;Mason Taylor;T'Vondre Sweat;Demario Davis;Minkah Fitzpatrick;Cade Klubnik;Omar Cooper Jr.;Kenyon Sadiq;David Bailey
Eagles: Jalen Hurts;Saquon Barkley;Tank Bigsby;DeVonta Smith;Dallas Goedert;Jordan Mailata;Jalen Carter;Jihaad Campbell;Cooper DeJean;Cole Payton;Makai Lemon;Eli Stowers
Steelers: Aaron Rodgers;Will Howard;Jaylen Warren;Kaleb Johnson;DK Metcalf;Pat Freiermuth;Cameron Heyward;T.J. Watt;Joey Porter Jr.;Drew Allar;Germie Bernard;Daylen Everette
49ers: Brock Purdy;Christian McCaffrey;Kyle Juszczyk;Mike Evans;Christian Kirk;Ricky Pearsall;George Kittle;Trent Williams;Nick Bosa;Fred Warner;Kaelon Black;De'Zhaun Stribling;Romello Height
Seahawks: Sam Darnold;Zach Charbonnet;Jaxon Smith-Njigba;Rashid Shaheed;Cooper Kupp;AJ Barner;Byron Murphy II;Devon Witherspoon;Nick Emmanwori;Jadarian Price;Julian Neal;Bud Clark
Buccaneers: Baker Mayfield;Bucky Irving;Kenneth Gainwell;Emeka Egbuka;Jalen McMillan;Chris Godwin;Tez Johnson;Cade Otton;Vita Vea;Antoine Winfield Jr.;Ted Hurst;Rueben Bain Jr.;Josiah Trotter
Titans: Cam Ward;Tony Pollard;Tyjae Spears;Calvin Ridley;Elic Ayomanor;Gunnar Helm;Jeffery Simmons;Kevin Winston Jr.;Chimere Dike;Nick Singleton;Carnell Tate;Keldric Faulk
Commanders: Jayden Daniels;Jacory Croskey-Merritt;Rachaad White;Terry McLaurin;Luke McCaffrey;Chig Okonkwo;Laremy Tunsil;K'Lavon Chaisson;Mike Sainristil;Kaytron Allen;Antonio Williams;Sonny Styles
'''), other=T('''
Cardinals: Jeremiyah Love;Michael Wilson;Trey Benson;Carson Beck;Reggie Virgil;Chase Bisontis;Anquan Boldin;Kurt Warner;Larry Fitzgerald
Falcons: Bijan Robinson;Drake London;Michael Penix Jr.;Tua Tagovailoa;Jalon Walker;Avieon Terrell;Harold Perkins Jr.;Zachariah Branch;Michael Vick;Tony Gonzalez;Deion Sanders
Ravens: Zay Flowers;Nate Wiggins;Derrick Henry;Kyle Hamilton;Roquan Smith;Ja'Kobi Lane;Elijah Sarratt;Zion Young;Adam Randall;Josh Cuevas;Ray Lewis;Terrell Suggs;Jonathan Ogden;Joe Flacco
Bills: James Cook;Dalton Kincaid;Cole Bishop;Keon Coleman;Josh Allen;Dawson Knox;Skyler Bell;T.J. Parker;Davison Igbinosun;Jalon Kilgore;Zane Durant;LeSean McCoy;Thurman Thomas;Jim Kelly;Cornelius Bennett
Panthers: Bryce Young;Jonathan Mingo;Jalen Coker;Ja'Tavion Sanders;Xavier Legette;Tetairoa McMillan;Chris Brazzell II;Will Lee III;Monroe Freeling;Zakee Wheatley;Luke Kuechly
Bears: Caleb Williams;Roschon Johnson;Tyson Bagent;Rome Odunze;Colston Loveland;Luther Burden III;Dillon Thieneman;Sam Roush;Zavion Thomas;Miller Moss;Malik Muhammad;Jim McMahon;William Perry;Mike Singletary
Bengals: Ja'Marr Chase;Joe Burrow;Andrei Iosivas;Chase Brown;Amarius Mims;Kris Jenkins;Cashius Howell;Colbie Young;Tacario Davis;Jack Endries;Boomer Esiason;Anthony Muñoz
Browns: Quinshon Judkins;Cedric Tillman;Carson Schwesinger;Denzel Boston;Emmanuel McNeil-Warren;KC Concepcion;Taylen Green;Aaron Anderson;Joe Royer;Spencer Fano;Bernie Kosar;Joe Thomas;Ozzie Newsome
Cowboys: Brandon Aubrey;Luke Schoonmaker;Brevyn Spann-Ford;Cooper Beebe;Marist Liufau;Tyler Guyton;CeeDee Lamb;Javonte Williams;Dak Prescott;Caleb Downs;Jaishawn Barham;Malachi Lawrence;Anthony Smith;LT Overton;Michael Trigg;Dez Bryant;DeMarco Murray;Tony Romo;Michael Irvin;Troy Aikman
Broncos: Bo Nix;Marvin Mims Jr.;Audric Estime;Pat Surtain II;RJ Harvey;Dallen Bentley;Justin Joly;Taurean York;John Elway;Steve Atwater;Terrell Davis;Von Miller
Lions: Jared Goff;Brian Branch;Jahmyr Gibbs;Sam LaPorta;Amon-Ra St. Brown;Derrick Moore;Keith Abney II;Kendrick Law;Blake Miller;Luke Altmyer;Barry Sanders
Packers: Dontayvion Wicks;Luke Musgrave;Lukas Van Ness;Edgerrin Cooper;Javon Bullard;MarShawn Lloyd;Matthew Golden;Josh Jacobs;Brandon Cisse;Dani Dennis-Sutton;Domani Jackson;LeRoy Butler;Sterling Sharpe;James Lofton
Texans: CJ Stroud;Henry To'oTo'o;Will Anderson Jr.;Calen Bullock;Cade Stover;Jayden Higgins;Kamari Lassiter;Woody Marks;Nico Collins;Kayden McDonald;Keylan Rutledge;Marlin Klein;Lewis Bond;Noah Whittington;Andre Johnson
Colts: Anthony Richardson;Josh Downs;Anthony Gould;Alec Pierce;Daniel Jones;Tyler Warren;Jonathan Taylor;A.J. Haulcy;CJ Allen;Deion Burks;Caden Curry;Seth McGowan;Peyton Manning;Edgerrin James
Jaguars: Brenton Strange;Parker Washington;Tank Bigsby;Brian Thomas Jr.;Cam Little;Bhayshul Tuten;Trevor Lawrence;Albert Regis;Josh Cameron;Nate Boerkircher;J'Mari Taylor;Tanner Koziol;Maurice Jones-Drew;Tony Boselli
Chiefs: Xavier Worthy;Rashee Rice;Kenneth Walker III;Patrick Mahomes II;Emmett Johnson;Garrett Nussmeier;Mansoor Delane;Peter Woods;Cyrus Allen;Dante Hall;Christian Okoye
Raiders: Brock Bowers;Aidan O'Connell;Michael Mayer;Tre Tucker;Ashton Jeanty;Dont'e Thornton Jr.;Maxx Crosby;Fernando Mendoza;Jermod McCoy;Mike Washington Jr.;Roman Hemby;Bo Jackson;Howie Long;Tim Brown
Chargers: Quentin Johnston;Joe Alt;Junior Colson;Ladd McConkey;Justin Herbert;Omarion Hampton;Akheem Mesidor;Brenen Thompson;Genesis Smith;Isaiah World;Jake Slaughter;Antonio Gates;Dan Fouts
Rams: Kobie Turner;Puka Nacua;Blake Corum;Joshua Karty;Jared Verse;Kamren Kinchens;Kyren Williams;Matthew Stafford;CJ Daniels;Max Klare;Ty Simpson;Tim Keenan III;Myles Garrett;Eric Dickerson;Kurt Warner
Dolphins: De'Von Achane;Malik Washington;Chop Robinson;Caleb Douglas;Chris Bell;Jacob Rodriguez;Kevin Coleman Jr.;Bob Griese;Dan Marino
Vikings: Jordan Addison;Dallas Turner;Will Reichard;Aaron Jones Sr.;Justin Jefferson;Caleb Banks;Demond Claiborne;Jake Golday;Caleb Tiernan;Randy Moss;Cris Carter
Patriots: Christian Gonzalez;Kayshon Boutte;Drake Maye;Ja'Lynn Polk;Joe Milton III;TreVeyon Henderson;Behren Morton;Caleb Lomu;Eli Raridon;Rob Gronkowski;Tom Brady;Adam Vinatieri;Ty Law
Saints: Spencer Rattler;Chris Olave;Taysom Hill;Tyler Shough;Jordyn Tyson;Bryce Lance;Christen Miller;Oscar Delp;Archie Manning;Drew Brees;Alvin Kamara
Giants: Theo Johnson;Tyrone Tracy Jr.;Jaxson Dart;Malik Nabers;Arvell Reese;Colton Hood;Malachi Fields;Francis Mauigoa;Eli Manning;Lawrence Taylor
Jets: Braelon Allen;Breece Hall;Garrett Wilson;Cade Klubnik;David Bailey;Kenyon Sadiq;D'Angelo Ponds;Darrelle Revis
Eagles: Jalen Carter;Jeremiah Trotter;Will Shipley;Jalen Hurts;Saquon Barkley;Cole Payton;Makai Lemon;Jihaad Campbell;Deontae Lawson;Brian Westbrook;Eric Allen;Brian Dawkins
Steelers: Darnell Washington;Payton Wilson;Kaleb Johnson;T.J. Watt;Will Howard;Drew Allar;Daylen Everette;Germie Bernard;Lake McRee;Rod Woodson;Troy Polamalu;Jerome Bettis;Aaron Rodgers
49ers: Jake Moody;Jacob Cowing;Brock Purdy;Christian McCaffrey;Fred Warner;Kyle Juszczyk;De'Zhaun Stribling;Kaelon Black;Romello Height;Ephesians Prysock;Frank Gore;Jerry Rice;Roger Craig;Steve Young;Joe Montana
Seahawks: Devon Witherspoon;Jaxon Smith-Njigba;Zach Charbonnet;Byron Murphy II;George Holani;Sam Darnold;Jadarian Price;Emmanuel Henderson Jr.;Kam Chancellor;Richard Sherman;Steve Largent;Malcolm Smith
Buccaneers: Bucky Irving;Chris Braswell;Graham Barton;Jalen McMillan;Emeka Egbuka;Tez Johnson;Rueben Bain Jr.;Ted Hurst;Jalon Daniels;Mike Alstott;Warren Sapp
Titans: Tyjae Spears;Will Levis;T'Vondre Sweat;Calvin Ridley;Cam Ward;Elic Ayomanor;Carnell Tate;Keldric Faulk;Nick Singleton;Anthony Hill Jr.;Bruce Matthews;Warren Moon
Commanders: Jayden Daniels;Luke McCaffrey;Mike Sainristil;Jacory Croskey-Merritt;Terry McLaurin;Antonio Williams;Kaytron Allen;Sonny Styles;Athan Kaliakmanis;Robert Henry Jr.;Deebo Samuel;DeAngelo Hall;John Riggins;Art Monk
'''))

NFL_MIDNIGHT = dict(base=T('''
Bengals: Ja'Marr Chase;Joe Burrow
Vikings: Demond Claiborne;Justin Jefferson
Bills: James Cook;Skyler Bell;Josh Allen
49ers: Brock Purdy;Kaelon Black;De'Zhaun Stribling;Christian McCaffrey;Mike Evans
Falcons: Zachariah Branch;Drake London;Bijan Robinson
Cardinals: Marvin Harrison Jr.;Jeremiyah Love;Carson Beck
Jets: Omar Cooper Jr.;Kenyon Sadiq;Cade Klubnik;Breece Hall;Garrett Wilson
Rams: Myles Garrett;Ty Simpson;Matthew Stafford;Puka Nacua
Steelers: DK Metcalf;Germie Bernard;Drew Allar
Giants: Jaxson Dart;Malik Nabers;Arvell Reese
Chargers: Omarion Hampton;Justin Herbert
Broncos: Jaylen Waddle;Jonah Coleman;Bo Nix;RJ Harvey
Saints: Jordyn Tyson;Chris Olave;Tyler Shough
Lions: Jared Goff;Amon-Ra St. Brown;Jahmyr Gibbs
Chiefs: Kenneth Walker III;Emmett Johnson;Garrett Nussmeier;Patrick Mahomes II
Commanders: Kaytron Allen;Sonny Styles;Antonio Williams;Jayden Daniels
Raiders: Fernando Mendoza;Mike Washington Jr.;Brock Bowers;Ashton Jeanty
Bears: Colston Loveland;Caleb Williams
Cowboys: CeeDee Lamb;George Pickens;Dak Prescott;Caleb Downs
Texans: Nico Collins;CJ Stroud
Ravens: Ja'Kobi Lane;Derrick Henry;Lamar Jackson
Dolphins: De'Von Achane;Caleb Douglas;Chris Bell
Eagles: Jalen Hurts;Makai Lemon;Saquon Barkley
Titans: Cam Ward;Carnell Tate;Nick Singleton
Packers: Jordan Love;Micah Parsons
Seahawks: Jaxon Smith-Njigba;Sam Darnold;Jadarian Price
Jaguars: Josh Cameron;Brian Thomas Jr.;Trevor Lawrence
Browns: Harold Fannin Jr.;Quinshon Judkins;KC Concepcion;Denzel Boston
Patriots: Drake Maye;TreVeyon Henderson
Colts: Tyler Warren;Deion Burks;Jonathan Taylor
Buccaneers: Emeka Egbuka;Baker Mayfield;Ted Hurst
Panthers: Bryce Young;Chris Brazzell II;Tetairoa McMillan
'''), other=T('''
Bills: Andre Reed;Khalil Shakir;Ray Davis;DJ Moore;Jim Kelly
Bengals: Chase Brown;Chad Johnson
Browns: Carson Schwesinger;Josh Gordon;Jerry Jeudy;Taylen Green;Shedeur Sanders
Patriots: Danny Amendola;Julian Edelman;Tom Brady
Cowboys: Dez Bryant;Jason Witten;Troy Aikman;Tony Romo;Malachi Lawrence
Saints: Drew Brees;Oscar Delp;Bryce Lance
Titans: Eddie George;Vince Young;Warren Moon;Wan'Dale Robinson;Keldric Faulk
Lions: Herman Moore;Barry Sanders
Steelers: Hines Ward;Michael Pittman Jr.;Willie Parker;Eli Heidenreich
Giants: Isaiah Likely;Malachi Fields;Cam Skattebo;Eli Manning
Buccaneers: Jalen McMillan;Ronde Barber;Rueben Bain Jr.;Tom Brady
49ers: John Taylor;Roger Craig;Jerry Rice;George Kittle;Joe Montana
Eagles: LeSean McCoy;Cole Payton;Eli Stowers;Randall Cunningham;DeVonta Smith
Seahawks: Marshawn Lynch;Steve Largent
Falcons: Michael Vick
Bears: Rome Odunze;Luther Burden III;Zavion Thomas
Chiefs: Rashee Rice;Mansoor Delane;Peter Woods;Cyrus Allen;Travis Kelce
Colts: Reggie Wayne;Alec Pierce
Jets: Santana Moss
Broncos: Terrell Davis;Peyton Manning;John Elway
Chargers: Antonio Gates;Brenen Thompson
Texans: Andre Johnson
Vikings: Adrian Peterson;Jordan Addison;Randy Moss
Dolphins: Dan Marino;Kevin Coleman Jr.
Ravens: Elijah Sarratt
Rams: Max Klare;CJ Daniels
Packers: Brandon Cisse
Commanders: Athan Kaliakmanis
Jaguars: Travis Hunter
'''))

NBA_FLAGSHIP = dict(base=T('''
Hawks: Zaccharie Risacher;Jalen Johnson;Dyson Daniels;CJ McCollum;Asa Newell;Onyeka Okongwu;Nickeil Alexander-Walker;Kingston Flemings;Zuby Ejiofor;Henri Veesaar
Celtics: Payton Pritchard;Nikola Vučević;Jayson Tatum;Jaylen Brown;Derrick White;Hugo González;Bill Russell;Kevin Garnett;Larry Bird;Kevin McHale;Paul Pierce;Chris Cenac Jr.;Dillon Mitchell
Nets: Nic Claxton;Michael Porter Jr.;Nolan Traore;Ben Saraf;Egor Dëmin;Drake Powell;Danny Wolf;Mikel Brown Jr.;Joshua Jefferson
Hornets: Coby White;Brandon Miller;Miles Bridges;LaMelo Ball;Kon Knueppel;Ryan Kalkbrenner;Hannes Steinbach;Christian Anderson Jr.
Bulls: Anfernee Simons;Josh Giddey;Jalen Smith;Matas Buzelis;Patrick Williams;Collin Sexton;Tre Jones;Caleb Wilson;Dailyn Swain
Cavaliers: Jarrett Allen;Donovan Mitchell;Evan Mobley;James Harden;Sam Merrill;Jaylon Tyson;Max Strus;Meleek Thomas
Mavericks: Khris Middleton;Naji Marshall;P.J. Washington Jr.;Max Christie;Kyrie Irving;Klay Thompson;Cooper Flagg;Steve Nash;Derek Harper;Dirk Nowitzki;Morez Johnson Jr.;Sergio De Larrea;Tobi Lawal
Nuggets: Cameron Johnson;Peyton Watson;Jamal Murray;Christian Braun;Nikola Jokić;Tim Hardaway Jr.;Aaron Gordon;Carmelo Anthony;Trevon Brazile
Pistons: Jalen Duren;Cade Cunningham;Ausar Thompson;Tobias Harris;Kevin Huerter;Duncan Robinson;Isaiah Stewart;Ebuka Okorie
Warriors: Kristaps Porzingis;Jimmy Butler III;Draymond Green;Brandin Podziemski;Stephen Curry;Pat Spencer;Rick Barry;Yaxel Lendeborg
Rockets: Reed Sheppard;Fred VanVleet;Alperen Sengun;Amen Thompson;Kevin Durant;Jabari Smith Jr.;Steven Adams;Hakeem Olajuwon;Yao Ming;Bruce Thornton
Pacers: Ivica Zubac;Tyrese Haliburton;Andrew Nembhard;Obi Toppin;Jarace Walker;Pascal Siakam;T.J. McConnell;Braden Smith
Clippers: Brook Lopez;Darius Garland;Kawhi Leonard;Derrick Jones Jr.;Bradley Beal;John Collins;Bennedict Mathurin;Keaton Wagler
Lakers: LeBron James;Rui Hachimura;Austin Reaves;Luka Dončić;Deandre Ayton;Marcus Smart;Jake LaRavia;Kareem Abdul-Jabbar;Shaquille O'Neal;Magic Johnson;James Worthy;Cameron Carr
Grizzlies: Ty Jerome;Ja Morant;Zach Edey;Jaylen Wells;Cedric Coward;Walter Clayton Jr.;Santi Aldama;Cameron Boozer;Karim Lopez;Richie Saunders
Heat: Giannis Antetokounmpo;Norman Powell;Tyler Herro;Bam Adebayo;Jaime Jaquez Jr.;Andrew Wiggins;Kel'el Ware;Dwyane Wade;Ryan Conwell
Bucks: Kevin Porter Jr.;Myles Turner;Kyle Kuzma;Ryan Rollins;Bobby Portis Jr.;Oscar Robertson;Ray Allen;Giannis Antetokounmpo;Brayden Burries;Nate Ament
Timberwolves: Donte DiVincenzo;Julius Randle;Naz Reid;Rudy Gobert;Anthony Edwards;Jaden McDaniels;Ayo Dosunmu;Isaiah Evans
Pelicans: Dejounte Murray;Zion Williamson;Trey Murphy III;Jordan Poole;Jeremiah Fears;Derik Queen;Saddiq Bey
Knicks: Jordan Clarkson;Jalen Brunson;Josh Hart;Mikal Bridges;OG Anunoby;Karl-Anthony Towns;Miles McBride;Walt Frazier;Jack Kayil;Tyler Nickel
Thunder: Luguentz Dort;Jalen Williams;Isaiah Joe;Cason Wallace;Chet Holmgren;Shai Gilgeous-Alexander;Ajay Mitchell;Aday Mara;Bennett Stirtz
Magic: Desmond Bane;Franz Wagner;Paolo Banchero;Anthony Black;Wendell Carter;Jalen Suggs
76ers: Kelly Oubre;Tyrese Maxey;Joel Embiid;Paul George;VJ Edgecombe;Quentin Grimes;Allen Iverson;Labaron Philon Jr.
Suns: Mark Williams;Devin Booker;Dillon Brooks;Jalen Green;Grayson Allen;Khaman Maluach;Koa Peat
Trail Blazers: Damian Lillard;Jrue Holiday;Scoot Henderson;Shaedon Sharpe;Deni Avdija;Yang Hansen;Caleb Love
Kings: Zach Lavine;Russell Westbrook;Malik Monk;Domantas Sabonis;Keegan Murray;Maxime Raynaud;De'Andre Hunter;Mitch Richmond;Darius Acuff Jr.;Alex Karaban
Spurs: Stephon Castle;De'Aaron Fox;Keldon Johnson;Devin Vassell;Victor Wembanyama;Dylan Harper;Carter Bryant;David Robinson;Jayden Quaintance;Tarris Reed Jr.;Ja'Kobi Gillespie
Raptors: Brandon Ingram;Scottie Barnes;RJ Barrett;Gradey Dick;Immanuel Quickley;Collin Murray-Boyles;Vince Carter;Allen Graves;Jaden Bradley
Jazz: Jaren Jackson Jr.;Lauri Markkanen;Keyonte George;Ace Bailey;Jusuf Nurkić;Isaiah Collier;Darryn Peterson
Wizards: Alex Sarr;Trae Young;Will Riley;Bub Carrington;Bilal Coulibaly;Tre Johnson III;Kyshawn George;AJ Dybantsa;Felix Okpara
SuperSonics: Lenny Wilkens
'''), other=T('''
Pistons: Dennis Rodman
Hawks: Jonathan Kuminga;Joe Johnson;Spud Webb
Jazz: Karl Malone
Suns: Steve Nash;Collin Gillespie
Heat: Shaquille O'Neal
Clippers: Baba Miller
Thunder: Aaron Wiggins;Otega Oweh;Thomas Sorber
Knicks: Bill Cartwright;John Starks;Nate Robinson;Jamal Crawford;Landry Shamet
Lakers: Bronny James;Derek Fisher;JR Smith
Bucks: Cole Anthony
Rockets: Dorian Finney-Smith
Magic: Dwight Howard;Grant Hill;Moritz Wagner
Mavericks: Dereck Lively II;J.J. Barea;Jason Terry;Tyler Smith;Brandon Williams;Danté Exum;Daniel Gafford
76ers: Eric Gordon
SuperSonics: Gary Payton
Warriors: Monta Ellis;Quinten Post;Moses Moody;Will Richard
Celtics: Ray Allen;Tony Allen
Bulls: Steve Kerr;Noa Essengue
Hornets: Tidjane Salaün;Sion James
Pacers: Ben Sheppard
Grizzlies: Cam Spencer
Cavaliers: Dean Wade
Pelicans: Herbert Jones;Kevon Looney
Kings: Zach Randolph
'''))

SW_CHROME = dict(
base='''Obi-Wan Kenobi;Lezine;Chopper;Devon Izara;Wizzich Mozzer;General Maximilian Veers;Rune Haako;Tusken Raider Warrior;Baylan Skoll;Captain Kaido;Freck;Clone Captain Rex;Sy Snootles;Chewbacca;Rabé;Hamato Xiono;Ahsoka Tano;Davo Sculdun;At Attin frogdog;Icarus;Ezra Bridger;General Hux;Ben Quadinaros;Bo-Katan Kryze;Looti Vario;Sergeant Heert;Mace Windu;Nooma;General Grievous;Maz Kanata;Rey;Grogu;Grand Admiral Thrawn;Runai Sculdun;Hutt Sister;Ralakili;Poe Dameron;Moff Gideon;Hera Syndulla;Senator Oran;The Armorer;Qi'ra;Yoda;BB-8;D-O;The Mandalorian;Sabine Wren;Supervisor Lonni Jung;Vult Skerris;Dryden Vos;Anakin Skywalker;Finn;Colonel Aftab Ackbar;Zeb Orrelios;Shin Hati;Kylo Ren;Kanan Jarrus;Sidon Ithano;Klatooinian Crime Boss;Eedy Karn;Babu Frik;Cobb Vanth;Morgan Elsbeth;Ghorman Spider;Emperor Palpatine;Sergeant Gharial;Colonel Ward;Bobbajo;Haja Estree;Syril Karn;Commissioner Helgait;Erskin Semaj;Jyn Erso;Hype Fazon;Rook Kast;Scorn;Bix Caleen;Kuiil;Captain Enoch;Stekan Sculdun;Chirrut Îmwe;Han Solo;Imperial Inquisitor;Lieutenant Connix;Rose Tico;The Duchess of Plazir;Great Mother Lakesis;Drash;Jan Dodonna;Luke Skywalker;Niro;Captain Phasma;Jedi Master Sol;Omera;Vel Sartha;Kleya Marki;Huyang;Moff Tarkin;Bardi;Asajj Ventress;Supreme Leader Snoke;The Stranger;Captain Gilad Pellaeon;Cassian Andor;Pix the Tooka;Jace Rucklin;Ponda Baba;Raxshir;Noti;Jedi Master Indara;Hutt Brother;Mon Mothma;Leida Mothma;Dedra Meero;Owen Lars;Yaddle;Lovey;Massiff;Elia Kane;K-2SO;General Draven;Jod Na Nawood;Count Dooku;Bossk;Dobbu Scay;Imperial Remnant Snowtrooper;Ranzar "Ran" Malk;Luthen Rael;Bail Organa;Neel;Padmé Amidala;Zorii Bliss;Admiral Ackbar;Embo;Jawa;Saw Gerrera;Cinta Kaz;SM-33;Lyco Strata;Master Eeko-Dio Daki;Tallie Lintra;8D8;Greef Karga;Jabba the Hutt;Maul;Beela;Taun We;BDX Droid;Captain Peavey;Jedi Padawan Jecki Lon;Dreena;Supervisor Lagret;Beef;Luminara Unduli;Gatori;Captain Canady;Omega;Samm;Krrsantan;Spybot;Barriss Offee;B-1 Mercenary Droid;Jar Jar Binks;Boba Fett;Enza Rylanz;Clem Andor;Bubbles;C-3PO;Aayla Secura;Darth Maul;Cad Bane;Perrin Fertha;B2EMO;L3-37;Darth Vader;Plo Koon;Qui-Gon Jinn;Fennec Shand;Carro Rylanz;Brander Lawson;Hugo Durant;Leia Organa;Even Piell;Captain Typho;B-2 Mercenary Droid;Oathkeeper;Keibu;Gerdis;Lando Calrissian;Eleventh Brother;Vane;Mrs. Ikk;Dr. Royce Hemlock;Lord Janu;Droopy McCool;R2-D2;Oppo Rancisis;The Grand Inquisitor;Rotta the Hutt''',
auto='''Commander D'Acy;Peli Motto;Adi Gallia;Bendu;DJ;Tion Medon;Bala-Tik;Ryder Azadi;Klothow;Poggle the Lesser;Lieutenant Beyta;Amilyn Holdo;AZI-3;Beaumont Kin;Alexsandr Kallus;Bodhi Rook;Jedi Master Kratu;Duke Kayo Organa;Maarva Andor;Snap Wexley;Lok Durd;Ketsu Onyo;Captain Panaka;Lux Bonteri;Rio Durant;Sabé;Kravas Drezzer;Bandit Leader;Reva;Unkar Plutt;Quinlan Vos;Gha Nachkt;Lieutenant Mitaka;Seventh Sister;Gall Trayvis;Captain Brutus;IG-11;Val;Shaak Ti;Wrobie Tyce;Phee Genoa;The Client;Major Partagaz;Tay Kolma;Dr. Gorst;Brasso;Wilmon Paak;F;Yuko;Crane;Lah Zhima;Anée-San''',
insert='''Director Krennic;Greedo;Scout Trooper;The Emperor;Darth Sidious;Kit Fisto;Porg;Vice Admiral Holdo;Max Rebo;Clone Trooper;Kaydel Ko Connix;Queen Amidala;Anzellan;Trash Crab;Dokma;Ewok;Lava Meerkat;Loth-Cat;Myykian;Puffer Pig;Oki-Poki;Tooka Cat;Wookiee;Savage Opress;Imperial Remnant AT-AT Driver;Bai;Clang;Ghhhk;Houjix;Keeto;Kintan Strider;K'lor'slug;Mantellian Savrip;Minch;Molatar;Monnok;Ng'ok;R5-D4;Stormtrooper;Hutt Twins;Paz Vizsla;Tie Fighter Pilot;Jango Fett;Death Trooper;Clone Commander Cody;Imperial Red Guard;Chita;Fox-Ear;Grand Master;Lah Kara;Nakime;Ronin;Shad-Rah;Teto;Woopas''',
multi='''Clone Commander Cody / Darth Sidious;Cassian Andor / K-2SO;Han Solo / Chewbacca;Rey / Lando Calrissian;Captain Phasma / DJ;Chewbacca / Darth Vader;C-3PO / R2-D2;Dedra Meero / Luthen Rael;Jango Fett / Boba Fett;Jyn Erso / Mon Mothma;Darth Vader / Obi-Wan Kenobi;Rey / Unkar Plutt;Boba Fett / Han Solo;Garsa Fwip / Fennec Shand;Anakin Skywalker / Padmé Amidala;Sabé / Senator Palpatine;Jedi Master Sol / The Stranger;Padmé Amidala / C-3PO;Kleya Marki / Luthen Rael;Supreme Chancellor Palpatine / Mace Windu;Kylo Ren / Han Solo;IG-11 / Moff Gideon;Major Partagaz / Syril Karn / Dedra Meero;Cassian Andor / Kleya Marki / Mon Mothma;Rex / Ezra Bridger / Kanan Jarrus;Rey / Chewbacca / R2-D2;Syril Karn / Eedy Karn / Dedra Meero;Han Solo / Qi'ra / Dryden Vos;Leida Mothma / Mon Mothma / Perrin Fertha;Hera Syndulla / Mon Mothma / C-3PO;Darth Sidious / Darth Maul / Padmé Amidala;Koska Reeves / Bo-Katan Kryze / The Armorer;SM-33 / Jod Na Nawood / KB;Zorii Bliss / Poe Dameron / D-O;Ahsoka Tano / Huyang / Sabine Wren;Bodhi Rook / Saw Gerrera / Jyn Erso;Mace Windu / Jango Fett / Boba Fett;Babu Frik / Zorii Bliss / BB-8;BB-8 / D-O / Babu Frik;Drash / Krrsantan / Fennec Shand;Luke Skywalker / Han Solo / Chewbacca''',
)

SW_GALAXY = dict(
# Base cards are art cards with titles, not character names.
base='''The Mandalorian's Escape;Padmé Amidala vs. the Nexu;Anakin Skywalker's Sunset;General Grievous;Battle of Endor;Carbonite;On Hoth;C-3PO & Babu Frik;Cassian Andor & K-2SO;Chewbacca On Hoth;The Knights Of Ren;The Dark Lord;The Emperor;The Chosen One;Tarkin;Only Hope;The Queen of Naboo;It's A Trap!;Educating Luke;Jango Fett's Legacy;Jawas' Score;Maz Kanata;The Trinity of Evil;Cloud City Escape;Logray;"Look, Sir, Droids!";Peace Is A Lie;FOR MANDALORE;Poe Dameron & BB-8;Qui-Gon Jinn;Released From Carbonite;The Rematch;Sol;Shin Hati;The Twins;Three Bounty Hunters;The Stranger;Darth Vader;Luke Skywalker;The Falcon Escapes;Crait Showdown;Pull To The Light;Ahsoka Tano's Path;Trust the Force;Darth Vader at Hoth;We Meet Again, At Last;Can You Speak Bocce?;Grand Master Yoda;Grogu;Save The Dream;YAHOOO;You Need A Teacher;Power of the Dark Side;The Seeker;What Lies Beneath!;You're Not Actually Going Into an Asteroid Field?;Raider Ambush;Rebel Pilot;There Aren't Many Jedi Left;The Savior;Last Look Back;Vel Sartha;Bounty Hunters;Machines of Dominion;I Have You Now;Through the Asteroid Field;Scarif Attack;Into the Storm;A Chilly Reception;The Failed Execution;Unyielding;The Gift;Carbonite Captor;Fighting Back;The Clones Advance;Solo Standoff;Master And Apprentice;Celebration On Endor;Padmé Amidala In The Senate;Life On Hoth;Boba Fett;The Generals;Zorii Bliss;Rebel Base;Death Star Duel;Battle In the Arena;Vulture Droids;Naboo Space Battle;Obi-Wan Kenobi On The Run;Lando Calrissian;Aurra Sing;Count Dooku;Life in Exile;Ahsoka Tano and Sabine Wren;Smugglers;The Royal Guard;A New Day for Luke Skywalker;Imminent Danger;No Squeezie!;Grogu Reaches Out''',
auto='''SM-33;Bix Caleen;Jar Jar Binks;Kylo Ren;Finn;Am;Lando Calrissian;C-3PO;Chewbacca;Jedi Master Indara;Dedra Meero;Jecki Lon;Cassian Andor;General Hux;Commissioner Helgait;Hype Fazon;Rey;Huyang;Qi'ra;Ahsoka Tano;Obi-Wan Kenobi;The Armorer;Jyn Erso;Kanan Jarrus;Lok Durd;Anakin Skywalker;Han Solo;Darth Sidious;Shin Hati;The Grand Inquisitor;K-2SO;Bo-Katan Kryze;Sabé;Pokkit;Zorii Bliss;The Duchess;Jod Na Nawood;Vice Admiral Holdo;Jedi Master Sol;Grand Admiral Thrawn;Luke Skywalker;Reva;The Stranger;Hera Syndulla;Sabine Wren;Padmé Amidala;The Mandalorian;Darth Maul;Supreme Leader Snoke;Mace Windu;Unkar Plutt;Luthen Rael;Boba Fett;Cobb Vanth;IG-11;Fennec Shand''',
insert='''Bastila Shan;Canderous Ordo;Carth Onasi;HK-47;Jolee Bindo;Juhani;T3-M4;Mission Vao;Sith Soldier;Visas Marr;Darth Malak;Darth Sion;Atton Rand;Darth Revan;Jyn Erso;Cassian Andor;K-2SO;Director Krennic;Saw Gerrera;Admiral Raddus;Galen Erso;Baze Malbus;Chirrut Îmwe;Bodhi Rook;Mon Mothma;Bail Organa;Darth Vader;Grand Moff Tarkin;Leia Organa;Anakin Skywalker;Moff Gideon;Maul;Darth Sidious;The Stranger;Captain Phasma;Savage Opress;Fifth Brother;Kylo Ren;Mother Talzin;Grand Admiral Thrawn;Morgan Elsbeth;Cad Bane;Count Dooku;Ben (Obi-Wan) Kenobi;Ahsoka Tano;Luke Skywalker;Han Solo: Imperial Stormtrooper Outfit;Imperial TIE Fighter Pilot;Obi-Wan Kenobi;Darth Maul;Yoda;Rey;Mace Windu;Qui-Gon Jinn;Kanan Jarrus;Jabba the Hutt;Shin Hati;Jar Jar Binks;Dedra Meero;Jango Fett;Jod Na Nawood;Lando Calrissian;Luthen Rael;General Grievous;Wicket W. Warrick;Asajj Ventress;Kit Fisto;Padmé Amidala;Shaak Ti;Clone Troopers;Clone Commander Cody;Yaddle;Saesee Tiin;Even Piell;Plo Koon;Eeth Koth;Ki-Adi-Mundi;Adi Gallia;The Armorer;The Mandalorian;Sabine Wren;Paz Vizsla;Grogu;Ragnar Vizsla;Axe Woves;Bo-Katan Kryze;Koska Reeves;Bix Caleen;Hera Syndulla;Zorii Bliss;Vice Admiral Holdo;Kleya Marki''',
multi='''Cad Bane / Boba Fett;Dryden Vos / Maul;Asajj Ventress / Darth Maul;General Hux / General Pryde;Sabé / Obi-Wan Kenobi;Jod Na Nawood / Gunter;Mon Mothma / Kleya Marki;Jabba the Hutt / Lando Calrissian;Darth Sidious / Darth Vader;The Mandalorian / Fennec Shand;Huyang / Ahsoka Tano / Sabine Wren;Dedra Meero / Luthen Rael / Cassian Andor;Chewbacca / C-3PO / Han Solo;Maz Kanata / Chewbacca / Rey;Chancellor Palpatine / Jango Fett / Mace Windu;Sully Stark / Obi-Wan Kenobi / Kawlan Roken;Bodhi Rook / Galen Erso / Jyn Erso;Kaydel Connix / Poe Dameron / Rose Tico;Chewbacca / Han Solo / Dryden Vos;Cassian Andor / Mon Mothma / Luthen Rael / Bail Organa;Boba Fett / Darth Vader / Han Solo / Lando Calrissian;Finn / Captain Phasma / DJ / Rose Tico;BB-8 / Finn / Rey / Unkar Plutt;The Duchess / Commissioner Helgait / The Mandalorian / Bo-Katan Kryze''',
)
