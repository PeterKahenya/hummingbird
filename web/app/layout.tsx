import '@mantine/core/styles.css';

import { ColorSchemeScript, MantineProvider, mantineHtmlProps, createTheme, Container } from '@mantine/core';

export const metadata = {
  title: 'Hummingbird',
  description: 'Minimalist Payroll Processing Platform',
};

const theme = createTheme({
  fontFamily:'Roboto, sans-serif',
  colors: {
    'ocean-blue': ['#7AD1DD', '#5FCCDB', '#44CADC', '#2AC9DE', '#1AC2D9', '#11B7CD', '#09ADC3', '#0E99AC', '#128797', '#147885'],
    'bright-pink': ['#F0BBDD', '#ED9BCF', '#EC7CC3', '#ED5DB8', '#F13EAF', '#F71FA7', '#FF00A1', '#E00890', '#C50E82', '#AD1374'],
  },
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head>
        <ColorSchemeScript />
      </head>
      <body>
        <MantineProvider theme={theme}>
          <Container>{children}</Container>
          </MantineProvider>
      </body>
    </html>
  );
}